# provides the shared fastapi dependencies for the catalog service
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, HTTPException, Path, status
from security import matches_internal_key
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
limiter.enabled = settings.ratelimit_enabled


# rejects a request without a valid internal api key
def verify_internal_key(x_internal_key: str = Header(alias="X-Internal-Key")) -> None:
    if not matches_internal_key(x_internal_key, settings.internal_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"message": "Member access required.", "field": None},
)
_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"message": "Organisation not found.", "field": "organisation_id"},
)


# grants a platform admin the rights of an organisation owner
def _admin_membership(organisation_id: uuid.UUID, user_id: uuid.UUID) -> OrganisationMember:
    return OrganisationMember(
        organisation_id=organisation_id,
        user_id=user_id,
        role=OrganisationRole.owner,
    )


# builds a dependency that requires membership of the path's organisation
def get_org_member(
    minimum_role: OrganisationRole = OrganisationRole.member,
) -> Callable[..., Awaitable[OrganisationMember]]:
    # resolves the caller's membership of the requested organisation
    async def _dependency(
        organisation_id: uuid.UUID = Path(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrganisationMember:
        org = await OrganisationRepository(db).get_by_id(organisation_id)
        if org is None:
            raise _NOT_FOUND
        if current_user.is_admin:
            return _admin_membership(organisation_id, current_user.id)
        member = await OrganisationMemberRepository(db).get(organisation_id, current_user.id)
        if member is None:
            raise _FORBIDDEN
        if role_rank(member.role) < role_rank(minimum_role):
            raise _FORBIDDEN
        return member

    return _dependency


_EVENT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"message": "Event not found.", "field": "event_id"},
)
_NOT_EVENT_MANAGER = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"message": "Manager access required.", "field": None},
)


# builds a dependency that requires managing the path's event
def get_event_member(
    minimum_role: OrganisationRole = OrganisationRole.manager,
) -> Callable[..., Awaitable[OrganisationMember]]:
    # resolves the caller's membership of the event's organisation
    async def _dependency(
        event_id: uuid.UUID = Path(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrganisationMember:
        event = await EventRepository(db).get_by_id(event_id)
        if event is None:
            raise _EVENT_NOT_FOUND
        if current_user.is_admin:
            return _admin_membership(event.organisation_id, current_user.id)
        member = await OrganisationMemberRepository(db).get(event.organisation_id, current_user.id)
        if member is None or role_rank(member.role) < role_rank(minimum_role):
            raise _NOT_EVENT_MANAGER
        return member

    return _dependency


get_redis = create_redis_dependency(settings.redis_url)


# builds an organisation service for a request
def get_organisation_service(db: AsyncSession = Depends(get_db)) -> OrganisationService:
    return OrganisationService(
        OrganisationRepository(db),
        OrganisationMemberRepository(db),
        AuditService(),
    )


# builds an event service for a request
def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(
        db,
        EventRepository(db),
        OrganisationRepository(db),
        VenueRepository(db),
        AuditService(),
    )


# builds a ticket type service for a request
def get_ticket_type_service(db: AsyncSession = Depends(get_db)) -> TicketTypeService:
    return TicketTypeService(EventRepository(db), TicketTypeRepository(db), AuditService())


# builds a venue service for a request
def get_venue_service(db: AsyncSession = Depends(get_db)) -> VenueService:
    return VenueService(VenueRepository(db), AuditService())
