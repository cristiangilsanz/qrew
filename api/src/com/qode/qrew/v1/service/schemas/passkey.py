from datetime import datetime

from pydantic import BaseModel, Field


class PasskeyResponse(BaseModel):
    id: str
    name: str | None
    aaguid: str
    last_used_at: datetime | None
    created_at: datetime


class PasskeyListResponse(BaseModel):
    passkeys: list[PasskeyResponse]


class PasskeyRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
