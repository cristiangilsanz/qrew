import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.locking import redlock
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.event import EventStatus
from com.qode.qrew.v1.service.models.reservation import (
    Reservation,
    ReservationStatus,
)
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.models.ticket_type import TicketType
from com.qode.qrew.v1.service.repositories.event import EventRepository
from com.qode.qrew.v1.service.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.service.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket import transition_ticket
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class ReservationError(DomainError):
    """Raised when a reservation operation fails a domain rule."""


class TierBusyError(DomainError):
    """Raised when the ticket-type row is locked by another transaction."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReservationService:
    """Business logic for the reservation aggregate."""

    def __init__(
        self,
        session: AsyncSession,
        repo: ReservationRepository,
        event_repo: EventRepository,
        tier_repo: TicketTypeRepository,
        audit: AuditService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._event_repo = event_repo
        self._tier_repo = tier_repo
        self._audit = audit

    async def _lock_tier_nowait(self, ticket_type_id: uuid.UUID) -> TicketType | None:
        """SELECT ... FOR UPDATE NOWAIT on the tier; raise TierBusyError on conflict."""
        try:
            result = await self._session.execute(
                text(
                    "SELECT * FROM ticket_types "
                    "WHERE id = :id AND deleted_at IS NULL "
                    "FOR UPDATE NOWAIT"
                ).bindparams(id=ticket_type_id)
            )
        except DBAPIError as exc:
            raise TierBusyError(
                "Ticket type is being purchased by another caller",
                field="ticket_type_id",
            ) from exc
        row = result.mappings().first()
        if row is None:
            return None
        return await self._tier_repo.get_by_id(ticket_type_id)

    @traced("reservation.create")
    async def reserve(
        self,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        quantity: int,
        risk_score: int = 0,
        requires_review: bool = False,
    ) -> Reservation:
        """Atomically reserve `quantity` seats; raise on capacity or limit breach."""
        if quantity < 1:
            raise ReservationError("Quantity must be at least 1", field="quantity")
        async with redlock(f"event:{event_id}:reserve:{user_id}", ttl_seconds=10):
            event = await self._event_repo.get_by_id(event_id)
            if event is None:
                raise ReservationError("Event not found", field="event_id")
            if event.status != EventStatus.published:
                raise ReservationError("Event is not on sale", field="status")
            if quantity > event.max_tickets_per_user:
                raise ReservationError(
                    "Quantity exceeds the per-user maximum for this event",
                    field="quantity",
                )
            now = _now()
            if now < event.sale_starts_at or now > event.sale_ends_at:
                raise ReservationError("Sale window is closed", field="sale_window")
            tier = await self._lock_tier_nowait(ticket_type_id)
            if tier is None or tier.event_id != event_id:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            if tier.reserved_count + quantity > tier.capacity:
                raise ReservationError(
                    "Not enough capacity remaining", field="quantity"
                )
            held = await self._repo.active_quantity_for_user(user_id, event_id)
            if held + quantity > event.max_tickets_per_user:
                raise ReservationError(
                    "Would exceed your per-user ticket limit",
                    field="quantity",
                )
            expires_at = now + timedelta(seconds=settings.reservation_ttl_seconds)
            reservation = Reservation(
                user_id=user_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                quantity=quantity,
                status=ReservationStatus.reserved,
                expires_at=expires_at,
                risk_score=risk_score,
                requires_review=requires_review,
            )
            reservation = await self._repo.insert(reservation)
            for _ in range(quantity):
                self._session.add(
                    Ticket(
                        reservation_id=reservation.id,
                        event_id=event_id,
                        ticket_type_id=ticket_type_id,
                        owner_user_id=user_id,
                        state=TicketState.reserved,
                    )
                )
            tier.reserved_count = tier.reserved_count + quantity
            await self._session.flush()
            await self._record(
                AuditAction.RESERVATION_CREATED,
                actor_id=user_id,
                reservation_id=reservation.id,
                payload={
                    "event_id": str(event_id),
                    "ticket_type_id": str(ticket_type_id),
                    "quantity": quantity,
                },
            )
            return reservation

    @traced("reservation.cancel")
    async def cancel(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> Reservation:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found", field="reservation_id")
        if reservation.status in {
            ReservationStatus.cancelled,
            ReservationStatus.expired,
        }:
            return reservation
        if reservation.status == ReservationStatus.paid:
            raise ReservationError(
                "Paid reservations must be refunded, not cancelled",
                field="status",
            )
        async with redlock(f"reservation:{reservation_id}:lifecycle", ttl_seconds=10):
            tier = await self._lock_tier_nowait(reservation.ticket_type_id)
            if tier is None:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            reservation.status = ReservationStatus.cancelled
            for ticket in await self._repo.list_tickets(reservation.id):
                if ticket.state == TicketState.reserved:
                    await transition_ticket(
                        self._session,
                        ticket_id=ticket.id,
                        to_state=TicketState.cancelled,
                        reason="reservation_cancelled",
                        actor_id=actor_id,
                        audit=self._audit,
                    )
            tier.reserved_count = max(0, tier.reserved_count - reservation.quantity)
            await self._session.flush()
            await self._record(
                AuditAction.RESERVATION_CANCELLED,
                actor_id=actor_id,
                reservation_id=reservation.id,
                payload={"event_id": str(reservation.event_id)},
            )
            return reservation

    async def get_for_user(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> tuple[Reservation, list[Ticket]]:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found", field="reservation_id")
        tickets = await self._repo.list_tickets(reservation.id)
        return reservation, tickets

    async def _record(
        self,
        action: AuditAction,
        *,
        actor_id: uuid.UUID,
        reservation_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="reservation",
                entity_id=str(reservation_id),
                payload=payload,
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=action)
