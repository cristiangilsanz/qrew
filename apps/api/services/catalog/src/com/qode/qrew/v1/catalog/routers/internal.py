import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.core.database import get_db
from com.qode.qrew.v1.catalog.core.dependencies import verify_internal_key
from com.qode.qrew.v1.catalog.repositories.events.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.organisation import OrganisationMemberRepository

router = APIRouter(
    prefix="/_internal/events",
    include_in_schema=False,
    dependencies=[Depends(verify_internal_key)],
)


class _MembershipResponse(BaseModel):
    event_exists: bool
    is_member: bool
    venue_id: uuid.UUID | None = None


@router.get("/{event_id}/members/{user_id}", response_model=_MembershipResponse)
async def event_membership(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> _MembershipResponse:
    """Answers whether a user belongs to the organisation that owns an event."""
    event = await EventRepository(db).get_by_id(event_id)
    if event is None:
        return _MembershipResponse(event_exists=False, is_member=False)
    member = await OrganisationMemberRepository(db).get(event.organisation_id, user_id)
    return _MembershipResponse(
        event_exists=True, is_member=member is not None, venue_id=event.venue_id
    )
