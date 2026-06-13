import uuid
from datetime import datetime

from pydantic import BaseModel

from com.qode.qrew.v1.catalog.schemas.organisation import OrganisationPublicResponse
from com.qode.qrew.v1.catalog.schemas.venue import VenuePublicResponse


class PublicTicketTypeItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    capacity: int
    reserved_count: int
    available: int
    price_cents: int
    currency: str
    position: int


class PublicEventDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    sale_starts_at: datetime
    sale_ends_at: datetime
    max_tickets_per_user: int
    published_at: datetime | None
    organisation: OrganisationPublicResponse
    venue: VenuePublicResponse
    ticket_types: list[PublicTicketTypeItem]


class AvailabilityItem(BaseModel):
    id: uuid.UUID
    name: str
    available: int
    price_cents: int
    currency: str


class EventAvailabilityResponse(BaseModel):
    ticket_types: list[AvailabilityItem]
