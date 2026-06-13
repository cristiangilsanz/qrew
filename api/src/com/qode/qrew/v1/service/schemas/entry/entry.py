import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EntryValidateRequest(BaseModel):
    ticket_jwt: str = Field(..., min_length=1)


class EntryValidateResponse(BaseModel):
    allowed: bool
    reason: str | None
    ticket_id: uuid.UUID | None
    holder_user_id: uuid.UUID | None
    scanned_at: datetime
