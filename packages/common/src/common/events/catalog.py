from __future__ import annotations

import uuid

from pydantic import BaseModel


class OrganisationCreatedData(BaseModel):
    organisation_id: uuid.UUID
    name: str


class EventPublishedData(BaseModel):
    event_id: uuid.UUID
    organisation_id: uuid.UUID
    venue_id: uuid.UUID
    name: str
    starts_at: str
    ends_at: str


class EventCancelledData(BaseModel):
    event_id: uuid.UUID
    reason: str


class TicketTypeCreatedData(BaseModel):
    ticket_type_id: uuid.UUID
    event_id: uuid.UUID
    name: str
    price_cents: int
    currency: str
    capacity: int


class TicketTypeDeletedData(BaseModel):
    ticket_type_id: uuid.UUID
    event_id: uuid.UUID
