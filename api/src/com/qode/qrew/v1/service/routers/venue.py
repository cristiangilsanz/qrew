import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.api import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.idempotency import idempotent
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.models.venue import Venue
from com.qode.qrew.v1.service.repositories.venue import VenueRepository
from com.qode.qrew.v1.service.schemas.venue import (
    VenueCreateRequest,
    VenuePublicResponse,
    VenueResponse,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.venue import VenueError, VenueService

router = APIRouter(prefix="/venues", tags=["venues"])


def _service(db: AsyncSession) -> VenueService:
    return VenueService(VenueRepository(db), AuditService())


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VenueResponse:
    """Create a new venue."""
    del request
    try:
        venue = await _service(db).create_venue(
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
    summary="List venues with optional city and country filters",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def list_venues(
    request: Request,
    city: str | None = None,
    country: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> Page[VenuePublicResponse]:
    """List venues, optionally filtered by city or country."""
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = VenueRepository(db).list_query(city=city, country=country)
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
    summary="Read the public profile of a venue",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_public_venue(
    request: Request,
    venue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VenuePublicResponse:
    """Return the public profile of a venue."""
    del request
    venue = await VenueRepository(db).get_by_id(venue_id)
    if venue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Venue not found", "field": "venue_id"},
        )
    return _to_public(venue)
