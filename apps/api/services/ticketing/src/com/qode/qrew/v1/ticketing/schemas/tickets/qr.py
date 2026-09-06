# defines the request and response schemas for a ticket's qr code
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class QrIssueRequest(BaseModel):
    latitude: Decimal = Field(..., ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal = Field(..., ge=Decimal("-180"), le=Decimal("180"))
    # the handset's own verdict on the fix, absent where the platform has none
    location_is_mock: bool | None = None


class GateRequirements(BaseModel):
    """Declares which gate checks are switched on, so the client asks for no more
    than the server will actually evaluate."""

    reassertion: bool
    geofence: bool
    device_binding: bool
    attestation: bool
    location_integrity: bool


class QrResponse(BaseModel):
    ticket_id: uuid.UUID
    jwt: str
    jti: str
    issued_at: datetime
    expires_at: datetime
    rotates_at: datetime
