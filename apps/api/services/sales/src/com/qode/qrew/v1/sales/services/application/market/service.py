import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from com.qode.qrew.v1.sales.core.errors import DomainError
from com.qode.qrew.v1.sales.models.market import (
    MarketAssignment,
    MarketAssignmentState,
    MarketListing,
    MarketListingState,
    MarketQueueEntry,
)
from com.qode.qrew.v1.sales.repositories.market import MarketRepository
from com.qode.qrew.v1.sales.repositories.projections import EventContextRepository, TicketTypeInventoryRepository
from com.qode.qrew.v1.sales.services.application.audit import AuditService
from observability import traced

logger = structlog.get_logger(__name__)

_NATS_TIMEOUT = 5.0

_QUEUE_JOINED = "MARKET_QUEUE_JOINED"
_QUEUE_LEFT = "MARKET_QUEUE_LEFT"
_TICKET_LISTED = "MARKET_TICKET_LISTED"
_ASSIGNMENT_DECLINED = "MARKET_ASSIGNMENT_DECLINED"
_ASSIGNMENT_PAID = "MARKET_ASSIGNMENT_PAID"


class MarketError(DomainError):
    """Raised when a market operation violates a domain rule."""


def _now() -> datetime:
    return datetime.now(UTC)


class MarketService:
    def __init__(
        self,
        repo: MarketRepository,
        event_ctx_repo: EventContextRepository,
        inventory_repo: TicketTypeInventoryRepository,
        audit: AuditService,
        *,
        assignment_ttl_hours: int,
        listing_ttl_days: int,
    ) -> None:
        self._repo = repo
        self._event_ctx = event_ctx_repo
        self._inventory = inventory_repo
        self._audit = audit
        self._assignment_ttl = timedelta(hours=assignment_ttl_hours)
        self._listing_ttl = timedelta(days=listing_ttl_days)

    # ------------------------------------------------------------------ queue

    @traced("market.service.join_queue")
    async def join_queue(
        self, *, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> MarketQueueEntry:
        event_ctx = await self._event_ctx.get_by_event_id(event_id)
        if event_ctx is None or event_ctx.status != "published":
            raise MarketError("Event not found", field="event_id")

        now = _now()
        sale_closed = event_ctx.sale_ends_at is not None and now > event_ctx.sale_ends_at
        if not sale_closed:
            raise MarketError(
                "Resale queue is only available once the sale window has closed",
                field="event_id",
            )

        active_count = await self._repo.active_ticket_count_for_user(
            user_id=user_id, event_id=event_id
        )
        if active_count >= event_ctx.max_tickets_per_user:
            raise MarketError(
                "You already have the maximum number of tickets for this event",
                field="user_id",
            )

        existing = await self._repo.get_queue_entry(event_id=event_id, user_id=user_id)
        if existing is not None:
            return existing

        entry = MarketQueueEntry(
            event_id=event_id,
            user_id=user_id,
            tiebreak=secrets.randbits(16),
        )
        entry = await self._repo.insert_queue_entry(entry)
        await self._record(_QUEUE_JOINED, actor_id=user_id, entity_id=str(event_id))
        return entry

    @traced("market.service.leave_queue")
    async def leave_queue(self, *, user_id: uuid.UUID, event_id: uuid.UUID) -> bool:
        entry = await self._repo.get_queue_entry(event_id=event_id, user_id=user_id)
        if entry is None:
            return False
        entry.left_at = _now()
        await self._repo.flush()
        await self._record(_QUEUE_LEFT, actor_id=user_id, entity_id=str(event_id))
        return True

    @traced("market.service.queue_status")
    async def queue_status(
        self, *, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> dict[str, Any]:
        entry = await self._repo.get_queue_entry(event_id=event_id, user_id=user_id)
        pending = await self._repo.get_pending_assignment_for_user(
            buyer_user_id=user_id, event_id=event_id
        )
        active_count = await self._repo.active_queue_count(event_id)
        return {
            "in_queue": entry is not None,
            "joined_at": entry.joined_at if entry else None,
            "pending_assignment_id": str(pending.id) if pending else None,
            "queue_count": active_count,
        }

    @traced("market.service.my_queues")
    async def my_queues(self, *, user_id: uuid.UUID) -> list[dict[str, Any]]:
        entries = await self._repo.get_active_queue_entries_for_user(user_id=user_id)
        return [{"event_id": e.event_id, "joined_at": e.joined_at} for e in entries]

    # ----------------------------------------------------------------- listing

    @traced("market.service.list_ticket")
    async def list_ticket(
        self, *, user_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> MarketListing:
        # Verify the ticket belongs to the caller and is in `issued` state
        ticket_row = await self._get_ticket_for_listing(user_id, ticket_id)
        event_id: uuid.UUID = ticket_row["event_id"]
        ticket_type_id: uuid.UUID = ticket_row["ticket_type_id"]

        event_ctx = await self._event_ctx.get_by_event_id(event_id)
        if event_ctx is None or event_ctx.status != "published":
            raise MarketError("Event not found", field="event_id")

        now = _now()
        sale_closed = event_ctx.sale_ends_at is not None and now > event_ctx.sale_ends_at
        if not sale_closed:
            raise MarketError(
                "Tickets can only be listed after the sale window closes",
                field="event_id",
            )

        if event_ctx.starts_at is not None and (event_ctx.starts_at - now).total_seconds() < 86400:
            raise MarketError(
                "Resale listing is closed within 24 hours of the event",
                field="event_id",
            )

        existing = await self._repo.get_listing_by_ticket_id(ticket_id)
        if existing is not None:
            raise MarketError("This ticket is already listed", field="ticket_id")

        inventory = await self._inventory.get_by_id(ticket_type_id)
        if inventory is None:
            raise MarketError("Ticket type not found", field="ticket_type_id")

        listing = MarketListing(
            ticket_id=ticket_id,
            event_id=event_id,
            seller_user_id=user_id,
            ticket_type_id=ticket_type_id,
            price_cents=inventory.price_cents,
            currency=inventory.currency or "EUR",
            state=MarketListingState.available,
            expires_at=now + self._listing_ttl,
        )
        listing = await self._repo.insert_listing(listing)

        await _freeze_ticket(ticket_id, actor_id=user_id)
        await self._record(_TICKET_LISTED, actor_id=user_id, entity_id=str(ticket_id))
        return listing

    async def get_listing_for_seller(
        self, *, user_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> MarketListing | None:
        return await self._repo.get_listing_by_ticket_id(ticket_id)

    # --------------------------------------------------------------- assignment

    @traced("market.service.get_assignment")
    async def get_assignment(
        self, *, user_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> MarketAssignment:
        assignment = await self._repo.get_assignment_by_id(assignment_id)
        if assignment is None or assignment.buyer_user_id != user_id:
            raise MarketError("Assignment not found", field="assignment_id")
        return assignment

    @traced("market.service.get_pending_assignment")
    async def get_pending_assignment(self, *, user_id: uuid.UUID) -> MarketAssignment | None:
        return await self._repo.get_pending_assignment_for_user_any_event(user_id)

    @traced("market.service.set_holders")
    async def set_holders(
        self,
        *,
        user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        holder_name: str,
        holder_dni: str,
    ) -> MarketAssignment:
        assignment = await self._repo.get_assignment_by_id(assignment_id)
        if assignment is None or assignment.buyer_user_id != user_id:
            raise MarketError("Assignment not found", field="assignment_id")
        if assignment.state != MarketAssignmentState.pending:
            raise MarketError("Assignment is no longer modifiable", field="state")
        if _now() >= assignment.expires_at:
            raise MarketError("Assignment has expired", field="expires_at")
        assignment.holder_name = holder_name
        assignment.holder_dni = holder_dni
        await self._repo.flush()
        return assignment

    @traced("market.service.get_payment_context")
    async def get_payment_context(
        self, *, user_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> dict[str, Any]:
        assignment = await self._repo.get_assignment_by_id(assignment_id)
        if assignment is None or assignment.buyer_user_id != user_id:
            raise MarketError("Assignment not found", field="assignment_id")
        if assignment.state != MarketAssignmentState.pending:
            raise MarketError("Assignment is not pending payment", field="state")
        if _now() >= assignment.expires_at:
            raise MarketError("Assignment has expired", field="expires_at")
        if not assignment.holder_name or not assignment.holder_dni:
            raise MarketError("Holder information must be set before payment", field="holder_name")

        listing = await self._repo.get_listing_by_id(assignment.listing_id)
        if listing is None:
            raise MarketError("Listing not found", field="listing_id")

        return {
            "amount_cents": listing.price_cents,
            "currency": listing.currency,
        }

    @traced("market.service.record_payment_intent")
    async def record_payment_intent(
        self,
        *,
        user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        payment_intent_id: str,
    ) -> None:
        assignment = await self._repo.get_assignment_by_id(assignment_id)
        if assignment is None or assignment.buyer_user_id != user_id:
            raise MarketError("Assignment not found", field="assignment_id")
        assignment.payment_intent_id = payment_intent_id
        await self._repo.flush()

    @traced("market.service.decline_assignment")
    async def decline_assignment(
        self, *, user_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> None:
        assignment = await self._repo.get_assignment_by_id(assignment_id)
        if assignment is None or assignment.buyer_user_id != user_id:
            raise MarketError("Assignment not found", field="assignment_id")
        if assignment.state != MarketAssignmentState.pending:
            raise MarketError("Assignment cannot be declined", field="state")

        assignment.state = MarketAssignmentState.declined
        await self._repo.flush()

        # Remove user from queue so they won't be re-assigned on this event
        entry = await self._repo.get_queue_entry(
            event_id=assignment.event_id, user_id=user_id
        )
        if entry is not None:
            entry.left_at = _now()
            await self._repo.flush()

        listing = await self._repo.get_listing_by_id(assignment.listing_id)
        if listing is not None and listing.state == MarketListingState.assigned:
            listing.state = MarketListingState.available
            await self._repo.flush()

        await self._record(_ASSIGNMENT_DECLINED, actor_id=user_id, entity_id=str(assignment_id))

    # ------------------------------------------------------------ settlement

    @traced("market.service.complete_assignment")
    async def complete_assignment(self, *, payment_intent_id: str) -> None:
        """Called when a market assignment payment succeeds (from payment webhook)."""
        assignment = await self._repo.get_assignment_by_payment_intent(payment_intent_id)
        if assignment is None:
            await logger.awarning(
                "market.complete_assignment.not_found",
                payment_intent_id=payment_intent_id,
            )
            return
        if assignment.state != MarketAssignmentState.pending:
            await logger.awarning(
                "market.complete_assignment.skip",
                state=assignment.state,
                assignment_id=str(assignment.id),
            )
            return

        listing = await self._repo.get_listing_by_id(assignment.listing_id)
        if listing is None:
            return

        assignment.state = MarketAssignmentState.paid
        assignment.paid_at = _now()
        listing.state = MarketListingState.completed
        listing.completed_at = _now()
        await self._repo.flush()

        await _publish_transfer(
            ticket_id=listing.ticket_id,
            new_owner_user_id=assignment.buyer_user_id,
            holder_name=assignment.holder_name or "",
            holder_dni=assignment.holder_dni or "",
            actor_id=assignment.buyer_user_id,
        )
        await self._record(
            _ASSIGNMENT_PAID,
            actor_id=assignment.buyer_user_id,
            entity_id=str(assignment.id),
        )

    # ----------------------------------------------------------------- helpers

    async def _get_ticket_for_listing(
        self, user_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> dict[str, Any]:
        row = await self._repo.get_ticket_for_listing(
            ticket_id=ticket_id, owner_user_id=user_id
        )
        if row is None:
            raise MarketError("Ticket not found", field="ticket_id")
        if row["state"] != "issued":
            raise MarketError(
                "Only issued tickets can be listed for resale", field="ticket_id"
            )
        return {"event_id": row["event_id"], "ticket_type_id": row["ticket_type_id"]}

    async def _record(self, action: str, *, actor_id: uuid.UUID, entity_id: str) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="market",
                entity_id=entity_id,
                payload={},
            )
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))


async def _freeze_ticket(ticket_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="ticket",
            aggregate_id=str(ticket_id),
            actor_id=str(actor_id),
            data={"ticket_id": str(ticket_id), "actor_id": str(actor_id)},
        )
        await nats_publish("market.ticket.freeze.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed", subject="market.ticket.freeze.v1", error=repr(exc)
        )


async def _publish_transfer(
    *,
    ticket_id: uuid.UUID,
    new_owner_user_id: uuid.UUID,
    holder_name: str,
    holder_dni: str,
    actor_id: uuid.UUID,
) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="ticket",
            aggregate_id=str(ticket_id),
            actor_id=str(actor_id),
            data={
                "ticket_id": str(ticket_id),
                "new_owner_user_id": str(new_owner_user_id),
                "holder_name": holder_name,
                "holder_dni": holder_dni,
            },
        )
        await nats_publish("market.transfer.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed", subject="market.transfer.v1", error=repr(exc)
        )
