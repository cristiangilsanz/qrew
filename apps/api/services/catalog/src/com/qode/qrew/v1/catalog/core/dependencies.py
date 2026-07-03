import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Path, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.catalog.core.database import get_db
from com.qode.qrew.v1.catalog.models.organisation import (
    OrganisationMember,
    OrganisationRole,
    role_rank,
)
from com.qode.qrew.v1.catalog.repositories.events.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.identity import UserRepository
from com.qode.qrew.v1.catalog.repositories.organisation import (
    OrganisationMemberRepository,
    OrganisationRepository,
)
from com.qode.qrew.v1.catalog.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository
from com.qode.qrew.v1.catalog.services.application.audit import AuditService
from com.qode.qrew.v1.catalog.services.application.events.event import EventService
from com.qode.qrew.v1.catalog.services.application.organisation import OrganisationService
from com.qode.qrew.v1.catalog.services.application.ticket_type import TicketTypeService
from com.qode.qrew.v1.catalog.services.application.venue import VenueService

from com.qode.qrew.v1.catalog.core.config import settings
from db import create_redis_dependency

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"message": "Not a member of this organisation", "field": None},
)
_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"message": "Organisation not found", "field": "organisation_id"},
)


def get_org_member(
    minimum_role: OrganisationRole = OrganisationRole.member,
) -> Callable[..., Awaitable[OrganisationMember]]:
    async def _dependency(
        organisation_id: uuid.UUID = Path(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrganisationMember:
        org = await OrganisationRepository(db).get_by_id(organisation_id)
        if org is None:
            raise _NOT_FOUND
        member = await OrganisationMemberRepository(db).get(organisation_id, current_user.id)
        if member is None:
            raise _FORBIDDEN
        if role_rank(member.role) < role_rank(minimum_role):
            raise _FORBIDDEN
        return member

    return _dependency


_EVENT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"message": "Event not found", "field": "event_id"},
)
_NOT_EVENT_MANAGER = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"message": "Not a manager of this organisation", "field": None},
)


def get_event_member(
    minimum_role: OrganisationRole = OrganisationRole.manager,
) -> Callable[..., Awaitable[OrganisationMember]]:
    async def _dependency(
        event_id: uuid.UUID = Path(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrganisationMember:
        event = await EventRepository(db).get_by_id(event_id)
        if event is None:
            raise _EVENT_NOT_FOUND
        member = await OrganisationMemberRepository(db).get(event.organisation_id, current_user.id)
        if member is None or role_rank(member.role) < role_rank(minimum_role):
            raise _NOT_EVENT_MANAGER
        return member

    return _dependency


get_redis = create_redis_dependency(settings.redis_url)


def get_organisation_service(db: AsyncSession = Depends(get_db)) -> OrganisationService:
    return OrganisationService(
        OrganisationRepository(db),
        OrganisationMemberRepository(db),
        UserRepository(db),
        AuditService(),
    )


def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(
        db,
        EventRepository(db),
        OrganisationRepository(db),
        VenueRepository(db),
        AuditService(),
    )


def get_ticket_type_service(db: AsyncSession = Depends(get_db)) -> TicketTypeService:
    return TicketTypeService(EventRepository(db), TicketTypeRepository(db), AuditService())


def get_venue_service(db: AsyncSession = Depends(get_db)) -> VenueService:
    return VenueService(VenueRepository(db), AuditService())
