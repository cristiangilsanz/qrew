# reads from the local projection whether a user belongs to an event's organisation
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.projections import (
    EventContext,
    OrganisationMemberContext,
)

logger = structlog.get_logger(__name__)


class CatalogUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class EventMembership:
    event_exists: bool
    is_member: bool
    venue_id: uuid.UUID | None


# answers from the projection catalog keeps up to date, without asking anyone
async def fetch_event_membership(
    session: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
) -> EventMembership:
    event = (
        await session.execute(
            select(EventContext).where(EventContext.event_id == event_id)
        )
    ).scalar_one_or_none()
    if event is None:
        return EventMembership(event_exists=False, is_member=False, venue_id=None)

    member = (
        await session.execute(
            select(OrganisationMemberContext).where(
                OrganisationMemberContext.organisation_id == event.organisation_id,
                OrganisationMemberContext.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return EventMembership(
        event_exists=True, is_member=member is not None, venue_id=event.venue_id
    )
