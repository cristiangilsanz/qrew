# reads and replaces the ticket holders named on a reservation
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.models.reservation_holder import ReservationHolder


class ReservationHolderRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # replaces every holder recorded for a reservation
    async def upsert_all(self, reservation_id: uuid.UUID, holders: list[ReservationHolder]) -> None:
        await self._session.execute(
            delete(ReservationHolder).where(ReservationHolder.reservation_id == reservation_id)
        )
        for h in holders:
            self._session.add(h)
        await self._session.flush()

    # lists a reservation's holders in position order
    async def list_by_reservation(self, reservation_id: uuid.UUID) -> list[ReservationHolder]:
        result = await self._session.execute(
            select(ReservationHolder)
            .where(ReservationHolder.reservation_id == reservation_id)
            .order_by(ReservationHolder.position)
        )
        return list(result.scalars().all())
