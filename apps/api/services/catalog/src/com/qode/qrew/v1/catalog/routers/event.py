import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pagination import Page, clamp_limit
from com.qode.qrew.v1.catalog.core.utils.pagination import cursor_paginate
from com.qode.qrew.v1.catalog.core.config import settings
from com.qode.qrew.v1.catalog.core.dependencies import (
    get_db,
    get_event_member,
    get_event_service,
    get_ticket_type_service,
    limiter,
)
from com.qode.qrew.v1.catalog.models.event import Event
from com.qode.qrew.v1.catalog.models.organisation import OrganisationMember, OrganisationRole
from com.qode.qrew.v1.catalog.models.ticket_type import TicketType
from com.qode.qrew.v1.catalog.schemas.event import (
    AvailabilityItem,
    EventAvailabilityResponse,
    EventResponse,
    EventSearchResult,
    EventUpdateRequest,
    PublicEventDetailResponse,
    PublicTicketTypeItem,
)
from com.qode.qrew.v1.catalog.schemas.organisation import OrganisationPublicResponse
from com.qode.qrew.v1.catalog.schemas.ticket_type import (
    TicketTypeCreateRequest,
    TicketTypeResponse,
    TicketTypeUpdateRequest,
)
from com.qode.qrew.v1.catalog.schemas.venue import VenuePublicResponse
from com.qode.qrew.v1.catalog.services.application.catalog import PublicCatalogService
from com.qode.qrew.v1.catalog.services.application.events.event import EventError, EventService
from com.qode.qrew.v1.catalog.services.application.events.search import SearchService
from com.qode.qrew.v1.catalog.services.application.ticket_type import (
    TicketTypeError,
    TicketTypeService,
)
from idempotency import idempotent
from locking import LockUnavailableError

router = APIRouter(prefix="/events", tags=["events"])

_search_service = SearchService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        organisation_id=event.organisation_id,
        venue_id=event.venue_id,
        name=event.name,
        description=event.description,
        image_url=event.image_url,
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


def _ticket_type_response(ticket_type: TicketType) -> TicketTypeResponse:
    return TicketTypeResponse(
        id=ticket_type.id,
        event_id=ticket_type.event_id,
        name=ticket_type.name,
        description=ticket_type.description,
        capacity=ticket_type.capacity,
        reserved_count=ticket_type.reserved_count,
        available=ticket_type.capacity - ticket_type.reserved_count,
        price_cents=ticket_type.price_cents,
        currency=ticket_type.currency,
        position=ticket_type.position,
        created_at=ticket_type.created_at,
    )


def _ticket_type_error(error: TicketTypeError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"event_id", "ticket_type_id"}
        else status.HTTP_409_CONFLICT
        if error.field == "name"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail={"message": error.message, "field": error.field})


# ---------------------------------------------------------------------------
# Event management (auth-gated)
# ---------------------------------------------------------------------------


@router.patch(
    "/{event_id}",
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
    svc: EventService = Depends(get_event_service),
) -> EventResponse:
    del request
    changes = body.model_dump(exclude_unset=True)
    try:
        event = await svc.update_event(actor_id=actor.user_id, event_id=event_id, changes=changes)
    except EventError as exc:
        raise _event_error(exc) from exc
    return _event_response(event)


@router.post(
    "/{event_id}/publish",
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
    svc: EventService = Depends(get_event_service),
) -> EventResponse:
    del request
    try:
        event = await svc.publish_event(actor_id=actor.user_id, event_id=event_id)
    except EventError as exc:
        raise _event_error(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another lifecycle change is in progress", "field": None},
        ) from exc
    return _event_response(event)


@router.post(
    "/{event_id}/cancel",
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
    svc: EventService = Depends(get_event_service),
) -> EventResponse:
    del request
    try:
        event = await svc.cancel_event(actor_id=actor.user_id, event_id=event_id)
    except EventError as exc:
        raise _event_error(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another lifecycle change is in progress", "field": None},
        ) from exc
    return _event_response(event)


# ---------------------------------------------------------------------------
# Ticket types (auth-gated, nested under events)
# ---------------------------------------------------------------------------


@router.post(
    "/{event_id}/ticket-types",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket type under an event",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def create_ticket_type(
    request: Request,
    event_id: uuid.UUID,
    body: TicketTypeCreateRequest,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    svc: TicketTypeService = Depends(get_ticket_type_service),
) -> TicketTypeResponse:
    del request
    try:
        ticket_type = await svc.create(
            actor_id=actor.user_id,
            event_id=event_id,
            name=body.name,
            description=body.description,
            capacity=body.capacity,
            price_cents=body.price_cents,
            currency=body.currency,
            position=body.position,
        )
    except TicketTypeError as exc:
        raise _ticket_type_error(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another ticket-type change is in progress", "field": None},
        ) from exc
    return _ticket_type_response(ticket_type)


@router.get(
    "/{event_id}/ticket-types",
    response_model=Page[TicketTypeResponse],
    status_code=status.HTTP_200_OK,
    summary="List ticket types for an event",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def list_ticket_types(
    request: Request,
    event_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
    svc: TicketTypeService = Depends(get_ticket_type_service),
    db: AsyncSession = Depends(get_db),
) -> Page[TicketTypeResponse]:
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = svc.list_for_event_query(event_id)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=TicketType.position,
        id_column=TicketType.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[TicketTypeResponse](
        items=[_ticket_type_response(row) for row in rows], next_cursor=next_cursor
    )


@router.patch(
    "/{event_id}/ticket-types/{ticket_type_id}",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a ticket type",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def update_ticket_type(
    request: Request,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    body: TicketTypeUpdateRequest,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    svc: TicketTypeService = Depends(get_ticket_type_service),
) -> TicketTypeResponse:
    del request
    changes = body.model_dump(exclude_unset=True)
    try:
        ticket_type = await svc.update(
            actor_id=actor.user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            changes=changes,
        )
    except TicketTypeError as exc:
        raise _ticket_type_error(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another ticket-type change is in progress", "field": None},
        ) from exc
    return _ticket_type_response(ticket_type)


@router.delete(
    "/{event_id}/ticket-types/{ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a ticket type",
)
@limiter.limit("60/hour")  # type: ignore[misc]
async def delete_ticket_type(
    request: Request,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    svc: TicketTypeService = Depends(get_ticket_type_service),
) -> None:
    del request
    try:
        await svc.delete(
            actor_id=actor.user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
        )
    except TicketTypeError as exc:
        raise _ticket_type_error(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another ticket-type change is in progress", "field": None},
        ) from exc


# ---------------------------------------------------------------------------
# Public catalog (no auth)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=Page[EventSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Public catalog list of events with cursor pagination and search",
)
@router.get(
    "/search",
    response_model=Page[EventSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search published events by text and filters",
    include_in_schema=False,
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def search_events(
    request: Request,
    q: str | None = Query(default=None, max_length=256),
    city: str | None = Query(default=None, max_length=128),
    cities: list[str] = Query(default=[]),
    category: str | None = Query(default=None, max_length=64),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
    cursor: str | None = None,
    limit: int = Query(default=settings.search_default_limit, ge=1),
    db: AsyncSession = Depends(get_db),
) -> Page[EventSearchResult]:
    del request
    page_limit = clamp_limit(limit, default=settings.search_default_limit)
    page_limit = min(page_limit, settings.search_max_limit)
    return await _search_service.search_events(
        db,
        q=q,
        city=city,
        cities=cities or None,
        category=category,
        from_=from_,
        to=to,
        cursor=cursor,
        limit=page_limit,
    )


@router.get(
    "/{event_id}",
    response_model=PublicEventDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a published event with embedded organisation, venue and tiers",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_public_event(
    request: Request,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PublicEventDetailResponse:
    del request
    svc = PublicCatalogService(db)
    result = await svc.get_published_event(event_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )
    event, org, venue = result
    tiers = await svc.get_ticket_types(event_id)
    return PublicEventDetailResponse(
        id=event.id,
        name=event.name,
        description=event.description,
        image_url=event.image_url,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        sale_starts_at=event.sale_starts_at,
        sale_ends_at=event.sale_ends_at,
        max_tickets_per_user=event.max_tickets_per_user,
        queue_required=event.queue_required,
        published_at=event.published_at,
        organisation=OrganisationPublicResponse(
            id=org.id, slug=org.slug, name=org.name, description=org.description
        ),
        venue=VenuePublicResponse(
            id=venue.id,
            name=venue.name,
            city=venue.city,
            country=venue.country,
            latitude=venue.latitude,
            longitude=venue.longitude,
            geofence_radius_m=venue.geofence_radius_m,
            timezone=venue.timezone,
        ),
        ticket_types=[
            PublicTicketTypeItem(
                id=tier.id,
                name=tier.name,
                description=tier.description,
                capacity=tier.capacity,
                reserved_count=tier.reserved_count,
                available=tier.capacity - tier.reserved_count,
                price_cents=tier.price_cents,
                currency=tier.currency,
                position=tier.position,
            )
            for tier in tiers
        ],
    )


@router.get(
    "/{event_id}/availability",
    response_model=EventAvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Lightweight availability projection for an event",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_event_availability(
    request: Request,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EventAvailabilityResponse:
    del request
    svc = PublicCatalogService(db)
    result = await svc.get_published_event_availability(event_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )
    _event, tiers = result
    return EventAvailabilityResponse(
        ticket_types=[
            AvailabilityItem(
                id=tier.id,
                name=tier.name,
                available=tier.capacity - tier.reserved_count,
                price_cents=tier.price_cents,
                currency=tier.currency,
            )
            for tier in tiers
        ]
    )
