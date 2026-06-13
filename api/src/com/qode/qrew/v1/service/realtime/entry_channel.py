import uuid

from com.qode.qrew.v1.service.core.ws import channel
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.repositories.event import EventRepository
from com.qode.qrew.v1.service.repositories.organisation import (
    OrganisationMemberRepository,
)
from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal

_PATTERN = "entry.{event_id}"


@channel(key_pattern=_PATTERN)
async def can_subscribe_entry(
    user: User, params: dict[str, str], session: Session
) -> bool:
    """Only members of the organisation that owns the event may subscribe."""
    del session
    event_id_raw = params.get("event_id")
    if not event_id_raw:
        return False
    try:
        event_id = uuid.UUID(event_id_raw)
    except ValueError:
        return False
    async with AsyncSessionLocal() as db:
        event = await EventRepository(db).get_by_id(event_id)
        if event is None:
            return False
        member = await OrganisationMemberRepository(db).get(
            event.organisation_id, user.id
        )
        return member is not None


def entry_channel_key(event_id: str) -> str:
    """Return the channel key for an event's entry feed."""
    return _PATTERN.format(event_id=event_id)
