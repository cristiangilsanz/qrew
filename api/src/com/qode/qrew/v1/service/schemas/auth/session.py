from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    jti: str
    ip_address: str | None
    user_agent: str | None
    device_fingerprint: str | None
    created_at: datetime
    last_used_at: datetime


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class RevokeAllResponse(BaseModel):
    message: str
