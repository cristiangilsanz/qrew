import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.repositories.projections import TicketTypeInventoryRepository
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from locking import redlock

logger = structlog.get_logger(__name__)


class SettlementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._reservations = ReservationRepository(session)
        self._inventory = TicketTypeInventoryRepository(session)

    async def mark_paid(self, reservation_id: uuid.UUID) -> Reservation | None:
        async with redlock(
            f"reservation:{reservation_id}:lifecycle",
            redis_url=settings.redis_url,
            ttl_seconds=10,
        ):
            reservation = await self._reservations.get_by_id(reservation_id)
            if reservation is None:
                return None
            if reservation.status != ReservationStatus.reserved:
                await logger.awarning(
                    "payment_events.succeeded.skip",
                    status=reservation.status.value,
                    reservation_id=str(reservation_id),
                )
                return None
            reservation.status = ReservationStatus.paid
            await self._session.commit()
        await _publish_paid(reservation)
        return reservation

    async def cancel(self, reservation_id: uuid.UUID, *, reason: str) -> Reservation | None:
        async with redlock(
            f"reservation:{reservation_id}:lifecycle",
            redis_url=settings.redis_url,
            ttl_seconds=10,
        ):
            reservation = await self._reservations.get_by_id(reservation_id)
            if reservation is None:
                return None
            if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired}:
                return None
            inventory = await self._inventory.get_by_id(reservation.ticket_type_id)
            reservation.status = ReservationStatus.cancelled
            if inventory is not None:
                inventory.reserved_count = max(0, inventory.reserved_count - reservation.quantity)
            await self._session.commit()
        await _publish_cancelled(reservation, reason=reason)
        return reservation


async def _publish_paid(reservation: Reservation) -> None:
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
        await nats_publish("sales.reservation.paid.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed", subject="sales.reservation.paid.v1", error=repr(exc)
        )


async def _publish_cancelled(reservation: Reservation, *, reason: str) -> None:
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
        await nats_publish("sales.reservation.cancelled.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.cancelled.v1",
            reason=reason,
            error=repr(exc),
        )
