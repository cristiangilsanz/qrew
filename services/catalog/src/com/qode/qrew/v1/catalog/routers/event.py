import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.routers import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.catalog.core.dependencies import get_event_member, get_org_member
from com.qode.qrew.v1.catalog.services.audit import AuditService
from idempotency import idempotent
from com.qode.qrew.v1.catalog.core.database import get_db
from com.qode.qrew.v1.catalog.core.dependencies import limiter
from locking import LockUnavailableError
from com.qode.qrew.v1.catalog.models.event import Event
from com.qode.qrew.v1.catalog.models.organisation import (
    OrganisationMember,
    OrganisationRole,
)
from com.qode.qrew.v1.catalog.repositories.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.organisation import OrganisationRepository
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository
from com.qode.qrew.v1.catalog.schemas.event import (
    EventCreateRequest,
    EventResponse,
    EventUpdateRequest,
)
from com.qode.qrew.v1.catalog.services.event import EventError, EventService

router = APIRouter(tags=["events"])


def _service(db: AsyncSession) -> EventService:
    return EventService(
        db,
        EventRepository(db),
        OrganisationRepository(db),
        VenueRepository(db),
        AuditService(),
    )


def _to_response(event: Event) -> EventResponse:
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


def _bad_request(error: EventError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"event_id", "organisation_id", "venue_id"}
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail={"message": error.message, "field": error.field})


@router.post(
    "/organisations/{organisation_id}/events",
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
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    del request
    try:
        event = await _service(db).create_event(
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
        raise _bad_request(exc) from exc
    return _to_response(event)


@router.get(
    "/organisations/{organisation_id}/events",
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
    db: AsyncSession = Depends(get_db),
) -> Page[EventResponse]:
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = _service(db).list_for_org_query(organisation_id)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=Event.created_at,
        id_column=Event.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[EventResponse](
        items=[_to_response(event) for event in rows], next_cursor=next_cursor
    )


@router.get(
    "/organisations/{organisation_id}/events/{event_id}",
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
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    del request
    event = await _service(db).get_by_id(event_id)
    if event is None or event.organisation_id != organisation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )
    return _to_response(event)


@router.patch(
    "/events/{event_id}",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a draft event",
)
@limiter.limit("60/hour")  # type: ignore[misc]
async def update_event(
    request: Request,
    event_id: uuid.UUID,
    body: EventUpdateRequest,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    del request
    changes = body.model_dump(exclude_unset=True)
    try:
        event = await _service(db).update_event(
            actor_id=actor.user_id, event_id=event_id, changes=changes
        )
    except EventError as exc:
        raise _bad_request(exc) from exc
    return _to_response(event)


@router.post(
    "/events/{event_id}/publish",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish a draft event",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def publish_event(
    request: Request,
    event_id: uuid.UUID,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    del request
    try:
        event = await _service(db).publish_event(actor_id=actor.user_id, event_id=event_id)
    except EventError as exc:
        raise _bad_request(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another lifecycle change is in progress", "field": None},
        ) from exc
    return _to_response(event)


@router.post(
    "/events/{event_id}/cancel",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an event",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def cancel_event(
    request: Request,
    event_id: uuid.UUID,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    del request
    try:
        event = await _service(db).cancel_event(actor_id=actor.user_id, event_id=event_id)
    except EventError as exc:
        raise _bad_request(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another lifecycle change is in progress", "field": None},
        ) from exc
    return _to_response(event)
