import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from com.qode.qrew.v1.catalog.models.event import EventStatus


class EventCreateRequest(BaseModel):
    venue_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    starts_at: datetime
    ends_at: datetime
    sale_starts_at: datetime
    sale_ends_at: datetime
    max_tickets_per_user: int = Field(default=4, ge=1, le=20)


class EventUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    sale_starts_at: datetime | None = None
    sale_ends_at: datetime | None = None
    max_tickets_per_user: int | None = Field(default=None, ge=1, le=20)
    queue_required: bool | None = None
    queue_admit_rate_per_minute: int | None = Field(default=None, ge=1, le=600)


class EventResponse(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    venue_id: uuid.UUID
    name: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    sale_starts_at: datetime
    sale_ends_at: datetime
    max_tickets_per_user: int
    status: EventStatus
    organiser_name: str
    venue_city: str
    queue_required: bool
    queue_admit_rate_per_minute: int
    created_at: datetime
    published_at: datetime | None
    cancelled_at: datetime | None
