import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pagination import Page, clamp_limit
from com.qode.qrew.v1.catalog.core.utils.pagination import cursor_paginate
from com.qode.qrew.v1.catalog.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.catalog.core.dependencies import get_db, get_venue_service, limiter
from com.qode.qrew.v1.catalog.models.venue import Venue
from com.qode.qrew.v1.catalog.schemas.venue import (
    VenueCreateRequest,
    VenuePublicResponse,
    VenueResponse,
)
from com.qode.qrew.v1.catalog.services.application.venue import VenueError, VenueService
from idempotency import idempotent

router = APIRouter(prefix="/venues", tags=["venues"])


def _to_response(venue: Venue) -> VenueResponse:
    return VenueResponse(
        id=venue.id,
        name=venue.name,
        address_line=venue.address_line,
        city=venue.city,
        country=venue.country,
        latitude=venue.latitude,
        longitude=venue.longitude,
        geofence_radius_m=venue.geofence_radius_m,
        timezone=venue.timezone,
        description=venue.description,
        created_at=venue.created_at,
    )


def _to_public(venue: Venue) -> VenuePublicResponse:
    return VenuePublicResponse(
        id=venue.id,
        name=venue.name,
        city=venue.city,
        country=venue.country,
        latitude=venue.latitude,
        longitude=venue.longitude,
        geofence_radius_m=venue.geofence_radius_m,
        timezone=venue.timezone,
    )


def _bad_request(error: VenueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": error.message, "field": error.field},
    )


@router.post(
    "",
    response_model=VenueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new venue",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def create_venue(
    request: Request,
    body: VenueCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    svc: VenueService = Depends(get_venue_service),
) -> VenueResponse:
    del request
    try:
        venue = await svc.create_venue(
            actor_id=current_user.id,
            name=body.name,
            address_line=body.address_line,
            city=body.city,
            country=body.country,
            latitude=body.latitude,
            longitude=body.longitude,
            geofence_radius_m=body.geofence_radius_m,
            timezone=body.timezone,
            description=body.description,
        )
    except VenueError as exc:
        raise _bad_request(exc) from exc
    return _to_response(venue)


@router.get(
    "",
    response_model=Page[VenuePublicResponse],
    status_code=status.HTTP_200_OK,
    summary="List venues",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def list_venues(
    request: Request,
    city: str | None = None,
    country: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    svc: VenueService = Depends(get_venue_service),
    db: AsyncSession = Depends(get_db),
) -> Page[VenuePublicResponse]:
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = svc.list_query(city=city, country=country)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=Venue.created_at,
        id_column=Venue.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[VenuePublicResponse](
        items=[_to_public(venue) for venue in rows], next_cursor=next_cursor
    )


@router.get(
    "/{venue_id}",
    response_model=VenuePublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a venue",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_public_venue(
    request: Request,
    venue_id: uuid.UUID,
    svc: VenueService = Depends(get_venue_service),
) -> VenuePublicResponse:
    del request
    venue = await svc.get_by_id(venue_id)
    if venue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Venue not found", "field": "venue_id"},
        )
    return _to_public(venue)
