import uuid
from datetime import datetime

from pydantic import BaseModel


class EventSearchResult(BaseModel):
    id: uuid.UUID
    name: str
    organiser_name: str | None = None
    venue_city: str | None = None
    starts_at: datetime | None = None
    rank: float | None = None
