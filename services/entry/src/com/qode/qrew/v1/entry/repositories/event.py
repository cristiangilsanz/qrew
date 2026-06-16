import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.catalog import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        result = await self._session.execute(
            select(Event).where(Event.id == event_id).limit(1)
        )
        return result.scalar_one_or_none()
