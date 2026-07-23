"""Expires timed-out assignments (24h) and auto-cancels expired listings (N days)."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.models.market import (
    MarketAssignment,
    MarketAssignmentState,
    MarketListingState,
)
from com.qode.qrew.v1.sales.repositories.market import MarketRepository
from locking import LockUnavailableError, redlock

logger = structlog.get_logger(__name__)

_NATS_TIMEOUT = 5.0


async def sweep_expired() -> tuple[int, int]:
    """
    Expires timed-out pending assignments and tries to re-assign.
    Cancels listings past their expires_at and returns the ticket to the seller.

    Returns (assignments_expired, listings_cancelled).
    """
    assignments_expired = await _expire_assignments()
    listings_cancelled = await _cancel_expired_listings()
    if assignments_expired or listings_cancelled:
        await logger.ainfo(
            "market.expirer.done",
            assignments_expired=assignments_expired,
            listings_cancelled=listings_cancelled,
        )
    return assignments_expired, listings_cancelled


async def _expire_assignments() -> int:
    expired = 0
    async with AsyncSessionLocal() as session:
        repo = MarketRepository(session)
        assignments = await repo.expired_pending_assignments(batch=100)

    for assignment in assignments:
        try:
            async with redlock(
                f"market:listing:{assignment.listing_id}:assign",
                redis_url=settings.redis_url,
                ttl_seconds=30,
            ):
                async with AsyncSessionLocal() as session:
                    repo = MarketRepository(session)

                    fresh = await repo.get_assignment_by_id(assignment.id)
                    if fresh is None or fresh.state != MarketAssignmentState.pending:
                        continue

                    fresh.state = MarketAssignmentState.expired

                    # Remove buyer from queue so they don't get re-assigned on this event
                    entry = await repo.get_queue_entry(
                        event_id=fresh.event_id, user_id=fresh.buyer_user_id
                    )
                    if entry is not None:
                        entry.left_at = datetime.now(UTC)

                    listing = await repo.get_listing_by_id(fresh.listing_id)
                    if listing is None:
                        await session.commit()
                        continue

                    # Get max_tickets_per_user for this event
                    result = await session.execute(
                        text(
                            "SELECT max_tickets_per_user FROM sales.event_context WHERE event_id = :eid"
                        ),
                        {"eid": listing.event_id},
                    )
                    row = result.mappings().first()
                    max_tickets = int(row["max_tickets_per_user"]) if row else 10

                    # Try to pick next random member (exclude all previously assigned users)
                    previous_ids = await repo.previously_assigned_user_ids(listing.id)
                    member = await repo.pick_random_queue_member(
                        event_id=listing.event_id,
                        exclude_user_ids=previous_ids,
                        max_tickets=max_tickets,
                    )

                    if member is not None:
                        new_expires = datetime.now(UTC) + timedelta(
                            hours=settings.market_assignment_ttl_hours
                        )
                        new_assignment = MarketAssignment(
                            listing_id=listing.id,
                            event_id=listing.event_id,
                            buyer_user_id=member.user_id,
                            expires_at=new_expires,
                            state=MarketAssignmentState.pending,
                        )
                        await repo.insert_assignment(new_assignment)
                        listing.state = MarketListingState.assigned
                        await session.commit()
                        await _publish_assigned(
                            assignment_id=new_assignment.id,
                            buyer_user_id=member.user_id,
                        )
                        await logger.ainfo(
                            "market.expirer.reassigned",
                            old_assignment_id=str(assignment.id),
                            new_assignment_id=str(new_assignment.id),
                        )
                    else:
                        listing.state = MarketListingState.available
                        await session.commit()
                        await logger.ainfo(
                            "market.expirer.no_members_left",
                            listing_id=str(listing.id),
                        )

                    expired += 1
        except LockUnavailableError:
            continue

    return expired


async def _cancel_expired_listings() -> int:
    cancelled = 0
    async with AsyncSessionLocal() as session:
        repo = MarketRepository(session)
        listings = await repo.expired_active_listings(batch=50)

    for listing in listings:
        try:
            async with redlock(
                f"market:listing:{listing.id}:assign",
                redis_url=settings.redis_url,
                ttl_seconds=30,
            ):
                async with AsyncSessionLocal() as session:
                    repo = MarketRepository(session)

                    fresh = await repo.get_listing_by_id(listing.id)
                    if fresh is None or fresh.state not in (
                        MarketListingState.available, MarketListingState.assigned
                    ):
                        continue

                    # Cancel any active assignment first
                    active = await repo.get_active_assignment_for_listing(fresh.id)
                    if active is not None:
                        active.state = MarketAssignmentState.expired

                    fresh.state = MarketListingState.cancelled
                    fresh.cancelled_at = datetime.now(UTC)
                    await session.commit()

                    # Return ticket to original seller
                    await _publish_listing_expired(
                        ticket_id=fresh.ticket_id,
                        seller_user_id=fresh.seller_user_id,
                    )
                    cancelled += 1
                    await logger.ainfo(
                        "market.expirer.listing_cancelled",
                        listing_id=str(fresh.id),
                    )
        except LockUnavailableError:
            continue

    return cancelled


async def _publish_assigned(*, assignment_id: object, buyer_user_id: object) -> None:
    try:
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="market_assignment",
            aggregate_id=str(assignment_id),
            actor_id=str(buyer_user_id),
            data={"assignment_id": str(assignment_id), "buyer_user_id": str(buyer_user_id)},
        )
        await nats_publish("market.assignment.created.v1", envelope)
    except Exception as exc:
        await logger.awarning("nats_publish_failed", subject="market.assignment.created.v1", error=repr(exc))


async def _publish_listing_expired(*, ticket_id: object, seller_user_id: object) -> None:
    try:
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="market_listing",
            aggregate_id=str(ticket_id),
            actor_id=str(seller_user_id),
            data={
                "ticket_id": str(ticket_id),
                "seller_user_id": str(seller_user_id),
            },
        )
        await nats_publish("market.listing.expired.v1", envelope)
    except Exception as exc:
        await logger.awarning("nats_publish_failed", subject="market.listing.expired.v1", error=repr(exc))
