# marks reservations as paid or cancelled and publishes the outcome
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from outbox import record as record_event

from com.qode.qrew.v1.sales.models.outbox import EventOutbox
from com.qode.qrew.v1.sales.core.config import settings
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.models.reservation_holder import ReservationHolder
from com.qode.qrew.v1.sales.models.reservation_item import ReservationItem
from com.qode.qrew.v1.sales.repositories.projections import TicketTypeInventoryRepository
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from locking import redlock

logger = structlog.get_logger(__name__)


class SettlementService:
    # stores the session and repositories the settlement service uses
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._reservations = ReservationRepository(session)
        self._inventory = TicketTypeInventoryRepository(session)

    # marks a reservation as paid and publishes its holders
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

            from com.qode.qrew.v1.sales.repositories.reservation_holder import (
                ReservationHolderRepository,
            )

            holders = await ReservationHolderRepository(self._session).list_by_reservation(
                reservation_id
            )
            items = await self._reservations.list_items(reservation_id)
            await _publish_paid(self._session, reservation, items, holders)
            await self._session.commit()
        return reservation

    # cancels a reservation and releases the inventory it held
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
            items = await self._reservations.list_items(reservation_id)
            for item in items:
                inventory = await self._inventory.get_by_id(item.ticket_type_id)
                if inventory is not None:
                    inventory.reserved_count = max(0, inventory.reserved_count - item.quantity)
            reservation.status = ReservationStatus.cancelled
            await _publish_cancelled(self._session, reservation, items, reason=reason)
            await self._session.commit()
        return reservation


# renders a reservation's tiers for a message payload
def _items_payload(items: list[ReservationItem]) -> list[dict[str, Any]]:
    return [
        {"ticket_type_id": str(item.ticket_type_id), "quantity": item.quantity} for item in items
    ]


# leaves in the outbox that a reservation was paid
async def _publish_paid(
    session: AsyncSession,
    reservation: Reservation,
    items: list[ReservationItem],
    holders: list[ReservationHolder],
) -> None:
    await record_event(
        session,
        EventOutbox,
        subject="sales.reservation.paid.v1",
        aggregate_type="reservation",
        aggregate_id=str(reservation.id),
        actor_id=str(reservation.user_id),
        data={
            "reservation_id": str(reservation.id),
            "user_id": str(reservation.user_id),
            "event_id": str(reservation.event_id),
            "items": _items_payload(items),
            "quantity": reservation.quantity,
            "holders": [
                {
                    "position": h.position,
                    "holder_name": h.holder_name,
                    "holder_document_type": h.holder_document_type,
                    "holder_dni": h.holder_dni,
                }
                for h in holders
            ],
        },
    )


# leaves in the outbox that a reservation was cancelled
async def _publish_cancelled(
    session: AsyncSession,
    reservation: Reservation,
    items: list[ReservationItem],
    *,
    reason: str,
) -> None:
    del reason
    await record_event(
        session,
        EventOutbox,
        subject="sales.reservation.cancelled.v1",
        aggregate_type="reservation",
        aggregate_id=str(reservation.id),
        actor_id=str(reservation.user_id),
        data={
            "reservation_id": str(reservation.id),
            "user_id": str(reservation.user_id),
            "event_id": str(reservation.event_id),
            "items": _items_payload(items),
            "quantity": reservation.quantity,
        },
    )
