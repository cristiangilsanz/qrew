import uuid
from datetime import datetime

from pydantic import BaseModel


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
