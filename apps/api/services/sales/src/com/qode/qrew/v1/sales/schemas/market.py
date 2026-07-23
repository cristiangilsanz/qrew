import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MarketQueueStatusResponse(BaseModel):
    in_queue: bool
    joined_at: datetime | None = None
    pending_assignment_id: uuid.UUID | None = None
    queue_count: int = 0


class MarketQueueJoinResponse(BaseModel):
    in_queue: bool
    joined_at: datetime


class MarketListingResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID
    price_cents: int
    currency: str
    state: str
    listed_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class MarketAssignmentResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    event_id: uuid.UUID
    price_cents: int
    currency: str
    state: str
    assigned_at: datetime
    expires_at: datetime
    holder_name: str | None = None
    holder_dni: str | None = None
    event_name: str | None = None
    ticket_type_name: str | None = None


class MarketSetHoldersRequest(BaseModel):
    holder_name: str = Field(..., min_length=1, max_length=255)
    holder_dni: str = Field(..., min_length=1, max_length=50)


class MarketAssignmentChargeResponse(BaseModel):
    amount_cents: int
    currency: str
