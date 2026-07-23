"""Picks a random queue member for each available market listing that has no active assignment."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.models.market import MarketAssignment, MarketAssignmentState, MarketListingState
from com.qode.qrew.v1.sales.repositories.market import MarketRepository
from locking import LockUnavailableError, redlock

logger = structlog.get_logger(__name__)


async def assign_pending() -> int:
    """Assigns a random queue member to each unassigned listing. Returns the count assigned."""
    assigned = 0
    async with AsyncSessionLocal() as session:
        repo = MarketRepository(session)
        listings = await repo.pick_available_listings_without_assignment(batch=50)

    for listing in listings:
        try:
            async with redlock(
                f"market:listing:{listing.id}:assign",
                redis_url=settings.redis_url,
                ttl_seconds=30,
            ):
                async with AsyncSessionLocal() as session:
                    repo = MarketRepository(session)

                    # Re-fetch under lock to avoid races
                    fresh = await repo.get_listing_by_id(listing.id)
                    if fresh is None or fresh.state != MarketListingState.available:
                        continue

                    active = await repo.get_active_assignment_for_listing(listing.id)
                    if active is not None:
                        continue

                    # Get the event's max_tickets_per_user
                    result = await session.execute(
                        text(
                            "SELECT max_tickets_per_user FROM sales.event_context WHERE event_id = :eid"
                        ),
                        {"eid": fresh.event_id},
                    )
                    row = result.mappings().first()
                    max_tickets = int(row["max_tickets_per_user"]) if row else 10

                    previous_ids = await repo.previously_assigned_user_ids(listing.id)

                    member = await repo.pick_random_queue_member(
                        event_id=fresh.event_id,
                        exclude_user_ids=previous_ids,
                        max_tickets=max_tickets,
                    )
                    if member is None:
                        await logger.ainfo(
                            "market.assigner.no_queue_members",
                            listing_id=str(listing.id),
                        )
                        continue

                    expires_at = datetime.now(UTC) + timedelta(
                        hours=settings.market_assignment_ttl_hours
                    )
                    assignment = MarketAssignment(
                        listing_id=fresh.id,
                        event_id=fresh.event_id,
                        buyer_user_id=member.user_id,
                        expires_at=expires_at,
                        state=MarketAssignmentState.pending,
                    )
                    await repo.insert_assignment(assignment)
                    fresh.state = MarketListingState.assigned
                    await session.commit()

                    await _publish_assigned(assignment_id=assignment.id, buyer_user_id=member.user_id)
                    assigned += 1
                    await logger.ainfo(
                        "market.assigner.assigned",
                        listing_id=str(listing.id),
                        assignment_id=str(assignment.id),
                        buyer_user_id=str(member.user_id),
                    )
        except LockUnavailableError:
            continue

    if assigned:
        await logger.ainfo("market.assigner.done", assigned=assigned)
    return assigned


async def _publish_assigned(*, assignment_id: object, buyer_user_id: object) -> None:
    try:
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="market_assignment",
            aggregate_id=str(assignment_id),
            actor_id=str(buyer_user_id),
            data={
                "assignment_id": str(assignment_id),
                "buyer_user_id": str(buyer_user_id),
            },
        )
        await nats_publish("market.assignment.created.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="market.assignment.created.v1",
            error=repr(exc),
        )
