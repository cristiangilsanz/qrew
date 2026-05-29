import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeviceResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    last_seen_at: datetime | None = None


class DeviceListResponse(BaseModel):
    devices: list[DeviceResponse]


class DeviceRevokeResponse(BaseModel):
    message: str


class DeviceRevokeAllResponse(BaseModel):
    message: str
    revoked_count: int


class DeviceBindBeginResponse(BaseModel):
    challenge: str


class DeviceBindCompleteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    public_key: str = Field(..., min_length=1, max_length=512)
    signature: str = Field(..., min_length=1, max_length=256)


class DeviceBindCompleteResponse(BaseModel):
    device_id: str
    message: str


class DeviceAttestRequest(BaseModel):
    platform: str = Field(..., pattern=r"^(android|ios)$")
    token: str = Field(..., min_length=1, max_length=16384)


class DeviceAttestResponse(BaseModel):
    message: str
    platform: str


class FingerprintReportRequest(BaseModel):
    fingerprint_hash: str = Field(..., min_length=1, max_length=255)
    user_agent: str | None = Field(default=None, max_length=1024)
    ip_address: str | None = Field(default=None, max_length=45)


class FingerprintReportResponse(BaseModel):
    message: str
    flagged: bool
