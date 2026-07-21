import uuid
from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field


class ScannerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    venue_id: uuid.UUID
    event_id: uuid.UUID
    date: date_type


class ScannerForEventRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    date: date_type | None = None


class ScannerRotateRequest(BaseModel):
    venue_id: uuid.UUID
    event_id: uuid.UUID
    date: date_type


class ScannerTokenResponse(BaseModel):
    scanner_id: uuid.UUID
    token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in_hours: int


class ScannerSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    venue_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    last_refreshed_at: datetime | None = None
    is_active: bool


class ScannerListResponse(BaseModel):
    scanners: list[ScannerSummaryResponse]


class ScannerDeactivateResponse(BaseModel):
    message: str
