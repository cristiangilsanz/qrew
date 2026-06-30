import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pagination import Page, clamp_limit
from com.qode.qrew.v1.catalog.core.utils.pagination import cursor_paginate
from com.qode.qrew.v1.catalog.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.catalog.core.dependencies import (
    get_db,
    get_event_service,
    get_org_member,
    get_organisation_service,
    limiter,
)
from com.qode.qrew.v1.catalog.models.event import Event
from com.qode.qrew.v1.catalog.models.organisation import (
    Organisation,
    OrganisationMember,
    OrganisationRole,
)
from com.qode.qrew.v1.catalog.schemas.event import EventCreateRequest, EventResponse
from com.qode.qrew.v1.catalog.schemas.organisation import (
    OrganisationCreateRequest,
    OrganisationMemberInviteRequest,
    OrganisationMemberResponse,
    OrganisationPublicResponse,
    OrganisationResponse,
)
from com.qode.qrew.v1.catalog.services.application.events.event import EventError, EventService
from com.qode.qrew.v1.catalog.services.application.organisation import (
    OrganisationError,
    OrganisationService,
)
from idempotency import idempotent

router = APIRouter(prefix="/organisations", tags=["organisations"])


def _bad_request(error: OrganisationError) -> HTTPException:
    code = status.HTTP_409_CONFLICT if error.field == "slug" else status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail={"message": error.message, "field": error.field})


def _to_response(org: Organisation) -> OrganisationResponse:
    return OrganisationResponse(
        id=org.id,
        slug=org.slug,
        name=org.name,
        description=org.description,
        created_at=org.created_at,
    )


def _event_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        organisation_id=event.organisation_id,
        venue_id=event.venue_id,
        name=event.name,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        sale_starts_at=event.sale_starts_at,
        sale_ends_at=event.sale_ends_at,
        max_tickets_per_user=event.max_tickets_per_user,
        status=event.status,
        organiser_name=event.organiser_name,
        venue_city=event.venue_city,
        queue_required=event.queue_required,
        queue_admit_rate_per_minute=event.queue_admit_rate_per_minute,
        created_at=event.created_at,
        published_at=event.published_at,
        cancelled_at=event.cancelled_at,
    )


def _event_error(error: EventError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"event_id", "organisation_id", "venue_id"}
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail={"message": error.message, "field": error.field})


@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organisation",
)
@limiter.limit("30/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def create_organisation(
    request: Request,
    body: OrganisationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    svc: OrganisationService = Depends(get_organisation_service),
) -> OrganisationResponse:
    del request
    try:
        org = await svc.create_organisation(
            owner_id=current_user.id,
            slug=body.slug,
            name=body.name,
            description=body.description,
        )
    except OrganisationError as exc:
        raise _bad_request(exc) from exc
    return _to_response(org)


@router.get(
    "",
    response_model=Page[OrganisationResponse],
    status_code=status.HTTP_200_OK,
    summary="List organisations the caller belongs to",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_my_organisations(
    request: Request,
    cursor: str | None = None,
    limit: int = 20,
    current_user: AuthenticatedUser = Depends(get_current_user),
    svc: OrganisationService = Depends(get_organisation_service),
    db: AsyncSession = Depends(get_db),
) -> Page[OrganisationResponse]:
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = svc.list_for_user_query(current_user.id)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=Organisation.created_at,
        id_column=Organisation.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[OrganisationResponse](
        items=[_to_response(org) for org in rows],
        next_cursor=next_cursor,
    )


@router.get(
    "/{organisation_id}",
    response_model=OrganisationPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Read the public profile of an organisation",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_public_organisation(
    request: Request,
    organisation_id: uuid.UUID,
    svc: OrganisationService = Depends(get_organisation_service),
) -> OrganisationPublicResponse:
    del request
    org = await svc.get_by_id(organisation_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Organisation not found", "field": "organisation_id"},
        )
    return OrganisationPublicResponse(
        id=org.id, slug=org.slug, name=org.name, description=org.description
    )


@router.post(
    "/{organisation_id}/members",
    response_model=OrganisationMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite an existing user to an organisation",
)
@limiter.limit("30/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def invite_member(
    request: Request,
    organisation_id: uuid.UUID,
    body: OrganisationMemberInviteRequest,
    actor: OrganisationMember = Depends(get_org_member(OrganisationRole.manager)),
    svc: OrganisationService = Depends(get_organisation_service),
) -> OrganisationMemberResponse:
    del request
    try:
        member = await svc.invite_member(
            actor_id=actor.user_id,
            organisation_id=organisation_id,
            invitee_email=str(body.email),
            role=body.role,
        )
    except OrganisationError as exc:
        raise _bad_request(exc) from exc
    return OrganisationMemberResponse(
        organisation_id=member.organisation_id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{organisation_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from an organisation",
)
@limiter.limit("30/hour")  # type: ignore[misc]
async def remove_member(
    request: Request,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
    actor: OrganisationMember = Depends(get_org_member(OrganisationRole.manager)),
    svc: OrganisationService = Depends(get_organisation_service),
) -> None:
    del request
    try:
        await svc.remove_member(
            actor_id=actor.user_id,
            organisation_id=organisation_id,
            member_user_id=user_id,
        )
    except OrganisationError as exc:
        raise _bad_request(exc) from exc


# ---------------------------------------------------------------------------
# Events nested under organisations
# ---------------------------------------------------------------------------


@router.post(
    "/{organisation_id}/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft event under an organisation",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def create_event(
    request: Request,
    organisation_id: uuid.UUID,
    body: EventCreateRequest,
    actor: OrganisationMember = Depends(get_org_member(OrganisationRole.manager)),
    svc: EventService = Depends(get_event_service),
) -> EventResponse:
    del request
    try:
        event = await svc.create_event(
            actor_id=actor.user_id,
            organisation_id=organisation_id,
            venue_id=body.venue_id,
            name=body.name,
            description=body.description,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            sale_starts_at=body.sale_starts_at,
            sale_ends_at=body.sale_ends_at,
            max_tickets_per_user=body.max_tickets_per_user,
        )
    except EventError as exc:
        raise _event_error(exc) from exc
    return _event_response(event)


@router.get(
    "/{organisation_id}/events",
    response_model=Page[EventResponse],
    status_code=status.HTTP_200_OK,
    summary="List events under an organisation",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def list_org_events(
    request: Request,
    organisation_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
    _actor: OrganisationMember = Depends(get_org_member(OrganisationRole.member)),
    svc: EventService = Depends(get_event_service),
    db: AsyncSession = Depends(get_db),
) -> Page[EventResponse]:
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = svc.list_for_org_query(organisation_id)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=Event.created_at,
        id_column=Event.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[EventResponse](
        items=[_event_response(event) for event in rows], next_cursor=next_cursor
    )


@router.get(
    "/{organisation_id}/events/{event_id}",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a single event the caller's organisation owns",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_org_event(
    request: Request,
    organisation_id: uuid.UUID,
    event_id: uuid.UUID,
    _actor: OrganisationMember = Depends(get_org_member(OrganisationRole.member)),
    svc: EventService = Depends(get_event_service),
) -> EventResponse:
    del request
    event = await svc.get_by_id(event_id)
    if event is None or event.organisation_id != organisation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )
    return _event_response(event)
