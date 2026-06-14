import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class QrIssueRequest(BaseModel):
    latitude: Decimal = Field(..., ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal = Field(..., ge=Decimal("-180"), le=Decimal("180"))


class QrResponse(BaseModel):
    ticket_id: uuid.UUID
    jwt: str
    jti: str
    issued_at: datetime
    expires_at: datetime
    rotates_at: datetime


class QrDeniedResponse(BaseModel):
    detail: dict[str, str | None]
