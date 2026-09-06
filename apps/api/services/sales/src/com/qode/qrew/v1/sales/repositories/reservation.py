# reads and writes reservations
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.models.reservation_item import ReservationItem


class ReservationRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # reads a reservation by its identifier
    async def get_by_id(self, reservation_id: uuid.UUID) -> Reservation | None:
        result = await self._session.execute(
            select(Reservation).where(Reservation.id == reservation_id)
        )
        return result.scalar_one_or_none()

    # writes a new reservation to the database
    async def insert(self, reservation: Reservation) -> Reservation:
        self._session.add(reservation)
        await self._session.flush()
        await self._session.refresh(reservation)
        return reservation

    # flushes pending changes to the database
    async def flush(self) -> None:
        await self._session.flush()

    # reads the ticket types and counts a reservation covers
    async def list_items(self, reservation_id: uuid.UUID) -> list[ReservationItem]:
        result = await self._session.execute(
            select(ReservationItem)
            .where(ReservationItem.reservation_id == reservation_id)
            .order_by(ReservationItem.ticket_type_id)
        )
        return list(result.scalars().all())

    # sums a user's tickets still held or paid for an event
    async def active_quantity_for_user(self, user_id: uuid.UUID, event_id: uuid.UUID) -> int:
        total = await self._session.execute(
            select(func.coalesce(func.sum(Reservation.quantity), 0))
            .where(Reservation.user_id == user_id)
            .where(Reservation.event_id == event_id)
            .where(Reservation.status.in_([ReservationStatus.reserved, ReservationStatus.paid]))
        )
        return int(total.scalar_one() or 0)
