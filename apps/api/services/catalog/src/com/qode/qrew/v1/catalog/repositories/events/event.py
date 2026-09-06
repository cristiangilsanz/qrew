# reads and writes events
import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.models.event import Event


class EventRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # reads an event by its identifier
    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        result = await self._session.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    # writes a new event to the database
    async def insert(self, event: Event) -> Event:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    # flushes pending changes to the database
    async def flush(self) -> None:
        await self._session.flush()

    # builds the query that lists an organisation's events
    def list_for_org_query(self, organisation_id: uuid.UUID) -> Select[tuple[Event]]:
        return select(Event).where(Event.organisation_id == organisation_id)
