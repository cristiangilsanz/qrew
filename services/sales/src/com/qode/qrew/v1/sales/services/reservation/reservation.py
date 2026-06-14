import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.services.audit import AuditService
from infra.errors import DomainError
from infra.locking import redlock
from observability import traced
from com.qode.qrew.v1.sales.models.projections import TicketTypeInventory
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.repositories.projections import (
    EventContextRepository,
    TicketTypeInventoryRepository,
)
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.settings import settings

logger = structlog.get_logger(__name__)

_RESERVATION_CREATED = "RESERVATION_CREATED"
_RESERVATION_CANCELLED = "RESERVATION_CANCELLED"


class ReservationError(DomainError):
    """Raised when a reservation operation fails a domain rule."""


class TierBusyError(DomainError):
    """Raised when the inventory record is temporarily unavailable due to a concurrent update."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReservationService:
    """Manages the full lifecycle of ticket reservations, including creation, cancellation, and inventory coordination."""

    def __init__(
        self,
        session: AsyncSession,
        repo: ReservationRepository,
        event_ctx_repo: EventContextRepository,
        inventory_repo: TicketTypeInventoryRepository,
        audit: AuditService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._event_ctx_repo = event_ctx_repo
        self._inventory_repo = inventory_repo
        self._audit = audit

    async def _lock_inventory_nowait(
        self, ticket_type_id: uuid.UUID
    ) -> TicketTypeInventory | None:
        try:
            result = await self._session.execute(
                text(
                    "SELECT ticket_type_id FROM sales.ticket_type_inventory "
                    "WHERE ticket_type_id = :id FOR UPDATE NOWAIT"
                ).bindparams(id=ticket_type_id)
            )
        except DBAPIError as exc:
            raise TierBusyError(
                "Ticket type is being purchased by another caller",
                field="ticket_type_id",
            ) from exc
        if result.first() is None:
            return None
        return await self._inventory_repo.get_by_id(ticket_type_id)

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
        if quantity < 1:
            raise ReservationError("Quantity must be at least 1", field="quantity")
        async with redlock(f"event:{event_id}:reserve:{user_id}", redis_url=settings.redis_url, ttl_seconds=10):
            event_ctx = await self._event_ctx_repo.get_by_event_id(event_id)
            if event_ctx is None:
                raise ReservationError("Event not found", field="event_id")
            if event_ctx.status != "published":
                raise ReservationError("Event is not on sale", field="status")
            if quantity > event_ctx.max_tickets_per_user:
                raise ReservationError(
                    "Quantity exceeds the per-user maximum for this event",
                    field="quantity",
                )
            now = _now()
            if event_ctx.sale_starts_at is None or event_ctx.sale_ends_at is None:
                raise ReservationError("Sale window not configured", field="sale_window")
            if now < event_ctx.sale_starts_at or now > event_ctx.sale_ends_at:
                raise ReservationError("Sale window is closed", field="sale_window")
            if event_ctx.queue_required:
                raise ReservationError(
                    "This event requires a queue token", field="queue_required"
                )
            inventory = await self._lock_inventory_nowait(ticket_type_id)
            if inventory is None or inventory.event_id != event_id:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            if inventory.reserved_count + quantity > inventory.capacity:
                raise ReservationError(
                    "Not enough capacity remaining", field="quantity"
                )
            held = await self._repo.active_quantity_for_user(user_id, event_id)
            if held + quantity > event_ctx.max_tickets_per_user:
                raise ReservationError(
                    "Would exceed your per-user ticket limit", field="quantity"
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
            inventory.reserved_count = inventory.reserved_count + quantity
            await self._session.flush()
            await self._record(
                _RESERVATION_CREATED,
                actor_id=user_id,
                reservation_id=reservation.id,
                payload={
                    "event_id": str(event_id),
                    "ticket_type_id": str(ticket_type_id),
                    "quantity": quantity,
                },
            )
        await _publish_reservation_created(reservation)
        return reservation

    @traced("reservation.reserve_with_queue_token")
    async def reserve_with_queue_token(
        self,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        quantity: int,
        risk_score: int = 0,
        requires_review: bool = False,
    ) -> Reservation:
        """Creates a reservation for events that require prior queue admission, assuming the queue token has already been validated."""
        if quantity < 1:
            raise ReservationError("Quantity must be at least 1", field="quantity")
        async with redlock(f"event:{event_id}:reserve:{user_id}", redis_url=settings.redis_url, ttl_seconds=10):
            event_ctx = await self._event_ctx_repo.get_by_event_id(event_id)
            if event_ctx is None:
                raise ReservationError("Event not found", field="event_id")
            if event_ctx.status != "published":
                raise ReservationError("Event is not on sale", field="status")
            if quantity > event_ctx.max_tickets_per_user:
                raise ReservationError(
                    "Quantity exceeds the per-user maximum for this event",
                    field="quantity",
                )
            now = _now()
            if event_ctx.sale_starts_at is None or event_ctx.sale_ends_at is None:
                raise ReservationError("Sale window not configured", field="sale_window")
            if now < event_ctx.sale_starts_at or now > event_ctx.sale_ends_at:
                raise ReservationError("Sale window is closed", field="sale_window")
            inventory = await self._lock_inventory_nowait(ticket_type_id)
            if inventory is None or inventory.event_id != event_id:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            if inventory.reserved_count + quantity > inventory.capacity:
                raise ReservationError(
                    "Not enough capacity remaining", field="quantity"
                )
            held = await self._repo.active_quantity_for_user(user_id, event_id)
            if held + quantity > event_ctx.max_tickets_per_user:
                raise ReservationError(
                    "Would exceed your per-user ticket limit", field="quantity"
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
            inventory.reserved_count = inventory.reserved_count + quantity
            await self._session.flush()
            await self._record(
                _RESERVATION_CREATED,
                actor_id=user_id,
                reservation_id=reservation.id,
                payload={
                    "event_id": str(event_id),
                    "ticket_type_id": str(ticket_type_id),
                    "quantity": quantity,
                },
            )
        await _publish_reservation_created(reservation)
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
        async with redlock(f"reservation:{reservation_id}:lifecycle", redis_url=settings.redis_url, ttl_seconds=10):
            inventory = await self._lock_inventory_nowait(reservation.ticket_type_id)
            if inventory is None:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            reservation.status = ReservationStatus.cancelled
            inventory.reserved_count = max(
                0, inventory.reserved_count - reservation.quantity
            )
            await self._session.flush()
            await self._record(
                _RESERVATION_CANCELLED,
                actor_id=actor_id,
                reservation_id=reservation.id,
                payload={"event_id": str(reservation.event_id)},
            )
        await _publish_reservation_cancelled(reservation)
        return reservation

    async def get_for_user(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> Reservation:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found", field="reservation_id")
        return reservation

    async def _record(
        self,
        action: str,
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


async def _publish_reservation_created(reservation: Reservation) -> None:
    try:
        from common.broker.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from common.events.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(reservation.id),
            actor_id=str(reservation.user_id),
            data={
                "reservation_id": str(reservation.id),
                "user_id": str(reservation.user_id),
                "event_id": str(reservation.event_id),
                "ticket_type_id": str(reservation.ticket_type_id),
                "quantity": reservation.quantity,
                "expires_at": reservation.expires_at.isoformat(),
            },
        )
        await nats_publish("sales.reservation.created.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.created.v1",
            error=repr(exc),
        )


async def _publish_reservation_cancelled(reservation: Reservation) -> None:
    try:
        from common.broker.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from common.events.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(reservation.id),
            actor_id=str(reservation.user_id),
            data={
                "reservation_id": str(reservation.id),
                "user_id": str(reservation.user_id),
                "event_id": str(reservation.event_id),
                "ticket_type_id": str(reservation.ticket_type_id),
                "quantity": reservation.quantity,
            },
        )
        await nats_publish("sales.reservation.cancelled.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.cancelled.v1",
            error=repr(exc),
        )
