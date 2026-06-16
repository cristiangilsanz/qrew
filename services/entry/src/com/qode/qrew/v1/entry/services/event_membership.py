import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.repositories.event import EventRepository
from com.qode.qrew.v1.entry.repositories.organisation import (
    OrganisationMemberRepository,
)


class EventNotFoundError(Exception):
    pass


class NotEventMemberError(Exception):
    pass


async def require_event_member(
    db: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    event = await EventRepository(db).get_by_id(event_id)
    if event is None:
        raise EventNotFoundError(event_id)
    member = await OrganisationMemberRepository(db).get(event.organisation_id, user_id)
    if member is None:
        raise NotEventMemberError(user_id)
