# defines the data schemas for catalog's domain events
from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel


# carries the event snapshot the four lifecycle subjects share
class _EventPayload(BaseModel):
    event_id: uuid.UUID
    organisation_id: uuid.UUID
    venue_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    sale_starts_at: datetime | None = None
    sale_ends_at: datetime | None = None
    max_tickets_per_user: int
    queue_required: bool
    queue_admit_rate_per_minute: int
    latitude: str | None = None
    longitude: str | None = None
    geofence_radius_m: int | None = None
    timezone: str | None = None


class EventPublishedData(_EventPayload):
    SUBJECT: ClassVar[str] = "catalog.event.published.v1"


class EventUpdatedData(_EventPayload):
    SUBJECT: ClassVar[str] = "catalog.event.updated.v1"


class EventOngoingData(_EventPayload):
    SUBJECT: ClassVar[str] = "catalog.event.ongoing.v1"


class EventCancelledData(_EventPayload):
    SUBJECT: ClassVar[str] = "catalog.event.cancelled.v1"


# carries the ticket type snapshot the created and updated subjects share
class _TicketTypePayload(BaseModel):
    ticket_type_id: uuid.UUID
    event_id: uuid.UUID
    capacity: int
    price_cents: int
    currency: str


class TicketTypeCreatedData(_TicketTypePayload):
    SUBJECT: ClassVar[str] = "catalog.ticket_type.created.v1"


class TicketTypeUpdatedData(_TicketTypePayload):
    SUBJECT: ClassVar[str] = "catalog.ticket_type.updated.v1"


class MembershipChangedData(BaseModel):
    SUBJECT: ClassVar[str] = "catalog.membership.changed.v1"

    organisation_id: uuid.UUID
    user_id: uuid.UUID
    role: str | None = None
