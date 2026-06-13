import uuid
from datetime import datetime

from pydantic import BaseModel


class EntryStatsResponse(BaseModel):
    event_id: uuid.UUID
    since: datetime
    total_issued: int
    total_entered: int
    total_remaining: int
    rejections_by_reason: dict[str, int]
    last_scan_at: datetime | None
