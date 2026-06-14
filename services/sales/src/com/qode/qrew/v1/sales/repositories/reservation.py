import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus


class ReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, reservation_id: uuid.UUID) -> Reservation | None:
        result = await self._session.execute(
            select(Reservation).where(Reservation.id == reservation_id)
        )
        return result.scalar_one_or_none()

    async def insert(self, reservation: Reservation) -> Reservation:
        self._session.add(reservation)
        await self._session.flush()
        await self._session.refresh(reservation)
        return reservation

    async def flush(self) -> None:
        await self._session.flush()

    async def active_quantity_for_user(
        self, user_id: uuid.UUID, event_id: uuid.UUID
    ) -> int:
        total = await self._session.execute(
            select(func.coalesce(func.sum(Reservation.quantity), 0))
            .where(Reservation.user_id == user_id)
            .where(Reservation.event_id == event_id)
            .where(
                Reservation.status.in_(
                    [ReservationStatus.reserved, ReservationStatus.paid]
                )
            )
        )
        return int(total.scalar_one() or 0)
