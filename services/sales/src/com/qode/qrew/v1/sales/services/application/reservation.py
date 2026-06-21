import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from jwt import InvalidTokenError
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.services.application.audit import AuditService
from com.qode.qrew.v1.sales.services.application.queue.storage import consume_reservation_token
from com.qode.qrew.v1.sales.core.errors import DomainError
from locking import redlock
from observability import traced
from com.qode.qrew.v1.sales.models.projections import TicketTypeInventory
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.repositories.projections import (
    EventContextRepository,
    TicketTypeInventoryRepository,
)
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.services.domain.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.domain.fraud.dependencies import build_engine_for_user
from com.qode.qrew.v1.sales.services.domain.fraud.engine import FraudDecision
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)

_RESERVATION_CREATED = "RESERVATION_CREATED"
_RESERVATION_CANCELLED = "RESERVATION_CANCELLED"

_NATS_PUBLISH_TIMEOUT = 5.0


class ReservationError(DomainError):
    """Raised when a reservation operation fails a domain rule."""


class TierBusyError(DomainError):
    """Raised when the inventory record is temporarily unavailable due to a concurrent update."""


class FraudBlockedError(DomainError):
    """Raised when a reservation attempt is blocked by the fraud engine."""


def _now() -> datetime:
    return datetime.now(UTC)


class ReservationService:
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

    async def _lock_inventory_nowait(self, ticket_type_id: uuid.UUID) -> TicketTypeInventory | None:
        # Single SELECT FOR UPDATE NOWAIT that both locks the row and returns fresh data,
        # avoiding the TOCTOU window of a separate lock query followed by a session.get().
        try:
            return await self._session.get(
                TicketTypeInventory,
                ticket_type_id,
                with_for_update={"nowait": True},
                populate_existing=True,
            )
        except DBAPIError as exc:
            raise TierBusyError(
                "Ticket type is being purchased by another caller",
                field="ticket_type_id",
            ) from exc

    @traced("reservation.create")
    async def reserve(
        self,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        ticket_type_id: uuid.UUID,
        quantity: int,
        ip_address: str | None = None,
        fingerprint_hash: str | None = None,
        reservation_window_token: str | None = None,
    ) -> Reservation:
        if quantity < 1:
            raise ReservationError("Quantity must be at least 1", field="quantity")

        engine = await build_engine_for_user(
            self._session, user_id=user_id, fingerprint_hash=fingerprint_hash
        )
        evaluation = await engine.evaluate(
            PurchaseContext(
                user_id=user_id,
                ip_address=ip_address,
                device_fingerprint_hash=fingerprint_hash,
                now=_now(),
            )
        )

        if evaluation.decision == FraudDecision.block:
            await self._record_blocked(
                actor_id=user_id, event_id=event_id, payload=evaluation.to_payload()
            )
            raise FraudBlockedError("Reservation rejected for risk")

        if reservation_window_token is not None:
            try:
                token_event = await consume_reservation_token(
                    token=reservation_window_token, user_id=user_id
                )
            except InvalidTokenError as exc:
                raise ReservationError(
                    "Reservation window token is invalid", field="reservation_window_token"
                ) from exc
            if token_event != event_id:
                raise ReservationError(
                    "Reservation window token is for a different event",
                    field="reservation_window_token",
                )

        async with redlock(
            f"event:{event_id}:reserve:{user_id}", redis_url=settings.redis_url, ttl_seconds=10
        ):
            event_ctx = await self._event_ctx_repo.get_by_event_id(event_id)
            if event_ctx is None:
                raise ReservationError("Event not found", field="event_id")
            if event_ctx.status != "published":
                raise ReservationError("Event is not on sale", field="status")
            if quantity > event_ctx.max_tickets_per_user:
                raise ReservationError(
                    "Quantity exceeds the per-user maximum for this event", field="quantity"
                )
            now = _now()
            if event_ctx.sale_starts_at is None or event_ctx.sale_ends_at is None:
                raise ReservationError("Sale window not configured", field="sale_window")
            if now < event_ctx.sale_starts_at or now > event_ctx.sale_ends_at:
                raise ReservationError("Sale window is closed", field="sale_window")
            if reservation_window_token is None and event_ctx.queue_required:
                raise ReservationError(
                    "Reservation window token is required for this event",
                    field="reservation_window_token",
                )
            inventory = await self._lock_inventory_nowait(ticket_type_id)
            if inventory is None or inventory.event_id != event_id:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            if inventory.reserved_count + quantity > inventory.capacity:
                raise ReservationError("Not enough capacity remaining", field="quantity")
            held = await self._repo.active_quantity_for_user(user_id, event_id)
            if held + quantity > event_ctx.max_tickets_per_user:
                raise ReservationError("Would exceed your per-user ticket limit", field="quantity")
            expires_at = now + timedelta(seconds=settings.reservation_ttl_seconds)
            reservation = Reservation(
                user_id=user_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                quantity=quantity,
                status=ReservationStatus.reserved,
                expires_at=expires_at,
                risk_score=evaluation.score,
                requires_review=evaluation.decision == FraudDecision.review,
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
            # Commit inside the lock so no concurrent holder sees uncommitted inventory changes.
            await self._session.commit()

        if evaluation.decision == FraudDecision.review:
            await self._record_flagged(
                actor_id=user_id,
                reservation_id=reservation.id,
                payload=evaluation.to_payload(),
            )

        await _publish_reservation_created(reservation)
        return reservation

    @traced("reservation.cancel")
    async def cancel(self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID) -> Reservation:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found", field="reservation_id")
        if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired}:
            return reservation
        if reservation.status == ReservationStatus.paid:
            raise ReservationError(
                "Paid reservations must be refunded, not cancelled", field="status"
            )
        async with redlock(
            f"reservation:{reservation_id}:lifecycle", redis_url=settings.redis_url, ttl_seconds=10
        ):
            inventory = await self._lock_inventory_nowait(reservation.ticket_type_id)
            if inventory is None:
                raise ReservationError("Ticket type not found", field="ticket_type_id")
            reservation.status = ReservationStatus.cancelled
            inventory.reserved_count = max(0, inventory.reserved_count - reservation.quantity)
            await self._session.flush()
            await self._record(
                _RESERVATION_CANCELLED,
                actor_id=actor_id,
                reservation_id=reservation.id,
                payload={"event_id": str(reservation.event_id)},
            )
            await self._session.commit()
        await _publish_reservation_cancelled(reservation)
        return reservation

    async def get_for_user(self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID) -> Reservation:
        reservation = await self._repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise ReservationError("Reservation not found", field="reservation_id")
        return reservation

    async def _record_blocked(
        self, *, actor_id: uuid.UUID, event_id: uuid.UUID, payload: dict[str, Any]
    ) -> None:
        try:
            await self._audit.record(
                action="RESERVATION_BLOCKED",
                actor_id=actor_id,
                entity_type="event",
                entity_id=str(event_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action="RESERVATION_BLOCKED", error=repr(exc)
            )

    async def _record_flagged(
        self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID, payload: dict[str, Any]
    ) -> None:
        try:
            await self._audit.record(
                action="RESERVATION_FLAGGED",
                actor_id=actor_id,
                entity_type="reservation",
                entity_id=str(reservation_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action="RESERVATION_FLAGGED", error=repr(exc)
            )

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
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))


async def _publish_reservation_created(reservation: Reservation) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

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
        await asyncio.wait_for(
            nats_publish("sales.reservation.created.v1", envelope),
            timeout=_NATS_PUBLISH_TIMEOUT,
        )
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.created.v1",
            error=repr(exc),
        )


async def _publish_reservation_cancelled(reservation: Reservation) -> None:
    try:
        from messaging.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

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
        await asyncio.wait_for(
            nats_publish("sales.reservation.cancelled.v1", envelope),
            timeout=_NATS_PUBLISH_TIMEOUT,
        )
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.cancelled.v1",
            error=repr(exc),
        )
