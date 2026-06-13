import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.core.infra.database import get_db
from com.qode.qrew.v1.catalog.core.infra.limiter import limiter
from com.qode.qrew.v1.catalog.models.event import EventStatus
from com.qode.qrew.v1.catalog.repositories.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.organisation import OrganisationRepository
from com.qode.qrew.v1.catalog.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.catalog.repositories.venue import VenueRepository
from com.qode.qrew.v1.catalog.schemas.organisation import OrganisationPublicResponse
from com.qode.qrew.v1.catalog.schemas.public_catalog import (
    AvailabilityItem,
    EventAvailabilityResponse,
    PublicEventDetailResponse,
    PublicTicketTypeItem,
)
from com.qode.qrew.v1.catalog.schemas.venue import VenuePublicResponse

router = APIRouter(prefix="/events", tags=["public-catalog"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": "Event not found", "field": "event_id"},
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
    event = await EventRepository(db).get_by_id(event_id)
    if event is None or event.status != EventStatus.published:
        raise _not_found()
    org = await OrganisationRepository(db).get_by_id(event.organisation_id)
    venue = await VenueRepository(db).get_by_id(event.venue_id)
    if org is None or venue is None:
        raise _not_found()
    stmt = TicketTypeRepository(db).list_for_event_query(event_id)
    result = await db.execute(stmt)
    tiers = result.scalars().all()
    return PublicEventDetailResponse(
        id=event.id,
        name=event.name,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        sale_starts_at=event.sale_starts_at,
        sale_ends_at=event.sale_ends_at,
        max_tickets_per_user=event.max_tickets_per_user,
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
    event = await EventRepository(db).get_by_id(event_id)
    if event is None or event.status != EventStatus.published:
        raise _not_found()
    stmt = TicketTypeRepository(db).list_for_event_query(event_id)
    result = await db.execute(stmt)
    tiers = result.scalars().all()
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
