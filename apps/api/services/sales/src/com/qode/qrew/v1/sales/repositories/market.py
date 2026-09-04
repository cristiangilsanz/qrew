# reads and writes the market's queue entries listings and assignments
import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.models.market import (
    MarketAssignment,
    MarketAssignmentState,
    MarketListing,
    MarketListingState,
    MarketQueueEntry,
)


class MarketRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # reads a user's active queue entry for an event
    async def get_queue_entry(
        self, *, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> MarketQueueEntry | None:
        result = await self._session.execute(
            select(MarketQueueEntry).where(
                MarketQueueEntry.event_id == event_id,
                MarketQueueEntry.user_id == user_id,
                MarketQueueEntry.left_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # lists a user's active queue entries across events
    async def get_active_queue_entries_for_user(
        self, *, user_id: uuid.UUID
    ) -> list[MarketQueueEntry]:
        result = await self._session.execute(
            select(MarketQueueEntry).where(
                MarketQueueEntry.user_id == user_id,
                MarketQueueEntry.left_at.is_(None),
            )
        )
        return list(result.scalars().all())

    # writes a new queue entry to the database
    async def insert_queue_entry(self, entry: MarketQueueEntry) -> MarketQueueEntry:
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    # counts an event's active queue entries
    async def active_queue_count(self, event_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                MarketQueueEntry.event_id == event_id,
                MarketQueueEntry.left_at.is_(None),
            )
        )
        return int(result.scalar_one() or 0)

    # counts a user's live tickets and pending assignments for an event
    async def active_ticket_count_for_user(self, *, user_id: uuid.UUID, event_id: uuid.UUID) -> int:
        ticket_count_sql = text(
            """
            SELECT COUNT(*) FROM ticketing.tickets
            WHERE owner_user_id = :user_id
              AND event_id = :event_id
              AND state IN ('reserved', 'issued', 'on_sale', 'frozen', 'scanning', 'flagged')
            """
        )
        result = await self._session.execute(
            ticket_count_sql, {"user_id": user_id, "event_id": event_id}
        )
        ticket_count = int(result.scalar_one() or 0)

        pending_assignments = await self._session.execute(
            select(func.count()).where(
                MarketAssignment.buyer_user_id == user_id,
                MarketAssignment.event_id == event_id,
                MarketAssignment.state == MarketAssignmentState.pending,
            )
        )
        assignment_count = int(pending_assignments.scalar_one() or 0)
        return ticket_count + assignment_count

    # reads a listing by its identifier
    async def get_listing_by_id(self, listing_id: uuid.UUID) -> MarketListing | None:
        return await self._session.get(MarketListing, listing_id)

    # reads a ticket's active listing
    async def get_listing_by_ticket_id(self, ticket_id: uuid.UUID) -> MarketListing | None:
        result = await self._session.execute(
            select(MarketListing).where(
                MarketListing.ticket_id == ticket_id,
                MarketListing.state.in_(
                    [MarketListingState.available, MarketListingState.assigned]
                ),
            )
        )
        return result.scalar_one_or_none()

    # lists a seller's active listings for an event
    async def get_active_listings_for_seller(
        self, *, seller_user_id: uuid.UUID, event_id: uuid.UUID
    ) -> list[MarketListing]:
        result = await self._session.execute(
            select(MarketListing).where(
                MarketListing.seller_user_id == seller_user_id,
                MarketListing.event_id == event_id,
                MarketListing.state.in_(
                    [MarketListingState.available, MarketListingState.assigned]
                ),
            )
        )
        return list(result.scalars().all())

    # writes a new listing to the database
    async def insert_listing(self, listing: MarketListing) -> MarketListing:
        self._session.add(listing)
        await self._session.flush()
        await self._session.refresh(listing)
        return listing

    # locks a batch of available listings that have no pending assignment
    async def pick_available_listings_without_assignment(
        self, batch: int = 50
    ) -> list[MarketListing]:
        result = await self._session.execute(
            text(
                """
                SELECT ml.id FROM sales.market_listings ml
                WHERE ml.state = 'available'
                  AND ml.expires_at > now()
                  AND NOT EXISTS (
                      SELECT 1 FROM sales.market_assignments ma
                      WHERE ma.listing_id = ml.id AND ma.state = 'pending'
                  )
                LIMIT :batch
                FOR UPDATE OF ml SKIP LOCKED
                """
            ),
            {"batch": batch},
        )
        ids = [row[0] for row in result.fetchall()]
        if not ids:
            return []
        listings_result = await self._session.execute(
            select(MarketListing).where(MarketListing.id.in_(ids))
        )
        return list(listings_result.scalars().all())

    # locks a random eligible queue member for an event
    async def pick_random_queue_member(
        self,
        *,
        event_id: uuid.UUID,
        exclude_user_ids: list[uuid.UUID],
        max_tickets: int,
    ) -> MarketQueueEntry | None:
        exclude_clause = ""
        params: dict[str, object] = {"event_id": event_id, "max_tickets": max_tickets}
        if exclude_user_ids:
            exclude_clause = "AND mq.user_id != ALL(:exclude_ids)"
            params["exclude_ids"] = exclude_user_ids

        result = await self._session.execute(
            text(
                f"""
                SELECT mq.id, mq.user_id FROM sales.market_queue_entries mq
                WHERE mq.event_id = :event_id
                  AND mq.left_at IS NULL
                  {exclude_clause}
                  AND (
                      SELECT COUNT(*) FROM ticketing.tickets t
                      WHERE t.owner_user_id = mq.user_id
                        AND t.event_id = :event_id
                        AND t.state IN ('reserved','issued','on_sale','frozen','scanning','flagged')
                  ) + (
                      SELECT COUNT(*) FROM sales.market_assignments ma
                      WHERE ma.buyer_user_id = mq.user_id
                        AND ma.event_id = :event_id
                        AND ma.state = 'pending'
                  ) < :max_tickets
                ORDER BY random()
                LIMIT 1
                FOR UPDATE OF mq SKIP LOCKED
                """
            ),
            params,
        )
        row = result.fetchone()
        if row is None:
            return None
        return await self._session.get(MarketQueueEntry, row[0])

    # locks a batch of listings whose deadline has passed
    async def expired_active_listings(self, batch: int = 50) -> list[MarketListing]:
        result = await self._session.execute(
            text(
                """
                SELECT id FROM sales.market_listings
                WHERE state IN ('available', 'assigned')
                  AND expires_at <= now()
                LIMIT :batch
                FOR UPDATE SKIP LOCKED
                """
            ),
            {"batch": batch},
        )
        ids = [row[0] for row in result.fetchall()]
        if not ids:
            return []
        listings_result = await self._session.execute(
            select(MarketListing).where(MarketListing.id.in_(ids))
        )
        return list(listings_result.scalars().all())

    # reads an assignment by its identifier
    async def get_assignment_by_id(self, assignment_id: uuid.UUID) -> MarketAssignment | None:
        return await self._session.get(MarketAssignment, assignment_id)

    # reads a listing's pending assignment if it has one
    async def get_active_assignment_for_listing(
        self, listing_id: uuid.UUID
    ) -> MarketAssignment | None:
        result = await self._session.execute(
            select(MarketAssignment).where(
                MarketAssignment.listing_id == listing_id,
                MarketAssignment.state == MarketAssignmentState.pending,
            )
        )
        return result.scalar_one_or_none()

    # reads a user's pending assignment for an event
    async def get_pending_assignment_for_user(
        self, *, buyer_user_id: uuid.UUID, event_id: uuid.UUID
    ) -> MarketAssignment | None:
        result = await self._session.execute(
            select(MarketAssignment).where(
                MarketAssignment.buyer_user_id == buyer_user_id,
                MarketAssignment.event_id == event_id,
                MarketAssignment.state == MarketAssignmentState.pending,
            )
        )
        return result.scalar_one_or_none()

    # reads a user's pending assignment across every event
    async def get_pending_assignment_for_user_any_event(
        self, buyer_user_id: uuid.UUID
    ) -> MarketAssignment | None:
        result = await self._session.execute(
            select(MarketAssignment).where(
                MarketAssignment.buyer_user_id == buyer_user_id,
                MarketAssignment.state == MarketAssignmentState.pending,
            )
        )
        return result.scalar_one_or_none()

    # lists the caller's assignments that are pending or ended recently
    async def list_recent_assignments_for_user(
        self, buyer_user_id: uuid.UUID, *, since: datetime, limit: int = 20
    ) -> list[MarketAssignment]:
        result = await self._session.execute(
            select(MarketAssignment)
            .where(
                MarketAssignment.buyer_user_id == buyer_user_id,
                or_(
                    MarketAssignment.state == MarketAssignmentState.pending,
                    MarketAssignment.assigned_at >= since,
                ),
            )
            .order_by(MarketAssignment.assigned_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # lists the users a listing has already been assigned to
    async def previously_assigned_user_ids(self, listing_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(MarketAssignment.buyer_user_id).where(
                MarketAssignment.listing_id == listing_id,
            )
        )
        return list(result.scalars().all())

    # locks a batch of pending assignments whose deadline has passed
    async def expired_pending_assignments(self, batch: int = 100) -> list[MarketAssignment]:
        result = await self._session.execute(
            text(
                """
                SELECT id FROM sales.market_assignments
                WHERE state = 'pending' AND expires_at <= now()
                LIMIT :batch
                FOR UPDATE SKIP LOCKED
                """
            ),
            {"batch": batch},
        )
        ids = [row[0] for row in result.fetchall()]
        if not ids:
            return []
        assignments_result = await self._session.execute(
            select(MarketAssignment).where(MarketAssignment.id.in_(ids))
        )
        return list(assignments_result.scalars().all())

    # writes a new assignment to the database
    async def insert_assignment(self, assignment: MarketAssignment) -> MarketAssignment:
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    # reads an assignment by its stripe payment intent
    async def get_assignment_by_payment_intent(
        self, payment_intent_id: str
    ) -> MarketAssignment | None:
        result = await self._session.execute(
            select(MarketAssignment).where(MarketAssignment.payment_intent_id == payment_intent_id)
        )
        return result.scalar_one_or_none()

    # reads the ticket a would be listing refers to
    async def get_ticket_for_listing(
        self, *, ticket_id: uuid.UUID, owner_user_id: uuid.UUID
    ) -> dict[str, object] | None:
        result = await self._session.execute(
            text(
                """
                SELECT event_id, ticket_type_id, state
                FROM ticketing.tickets
                WHERE id = :ticket_id AND owner_user_id = :user_id
                """
            ),
            {"ticket_id": ticket_id, "user_id": owner_user_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return {
            "event_id": uuid.UUID(str(row["event_id"])),
            "ticket_type_id": uuid.UUID(str(row["ticket_type_id"])),
            "state": str(row["state"]),
        }

    # flushes pending changes to the database
    async def flush(self) -> None:
        await self._session.flush()
