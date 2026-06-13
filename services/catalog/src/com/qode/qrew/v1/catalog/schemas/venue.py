import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class VenueCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    address_line: str = Field(..., min_length=1, max_length=256)
    city: str = Field(..., min_length=1, max_length=96)
    country: str = Field(..., min_length=2, max_length=2)
    latitude: Decimal = Field(..., ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal = Field(..., ge=Decimal("-180"), le=Decimal("180"))
    geofence_radius_m: int = Field(default=200, ge=50, le=5000)
    timezone: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=2000)


class VenueResponse(BaseModel):
    id: uuid.UUID
    name: str
    address_line: str
    city: str
    country: str
    latitude: Decimal
    longitude: Decimal
    geofence_radius_m: int
    timezone: str
    description: str | None
    created_at: datetime


class VenuePublicResponse(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    country: str
    latitude: Decimal
    longitude: Decimal
    geofence_radius_m: int
    timezone: str
