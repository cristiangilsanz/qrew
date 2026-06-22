import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.models.event import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        result = await self._session.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def insert(self, event: Event) -> Event:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def flush(self) -> None:
        await self._session.flush()

    def list_for_org_query(self, organisation_id: uuid.UUID) -> Select[tuple[Event]]:
        return select(Event).where(Event.organisation_id == organisation_id)
