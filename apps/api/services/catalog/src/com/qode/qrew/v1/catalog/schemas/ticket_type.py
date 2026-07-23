import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TicketTypeCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=2000)
    capacity: int = Field(..., ge=1, le=100_000)
    price_cents: int = Field(..., ge=0, le=10_000_000)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    position: int = Field(default=0, ge=0)


class TicketTypeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=2000)
    capacity: int | None = Field(default=None, ge=1, le=100_000)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    position: int | None = Field(default=None, ge=0)


class TicketTypeResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    name: str
    description: str | None
    capacity: int
    reserved_count: int
    available: int
    price_cents: int
    currency: str
    position: int
    created_at: datetime
