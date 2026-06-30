import uuid
from dataclasses import dataclass
from dataclasses import field as _field
from datetime import datetime
from enum import StrEnum


class EntryReason(StrEnum):
    signature = "signature"
    audience = "audience"
    expired = "expired"
    wrong_event = "wrong_event"
    wrong_venue = "wrong_venue"
    replay = "replay"
    not_found = "not_found"
    wrong_owner = "wrong_owner"
    state = "state"
    busy = "busy"


@dataclass(frozen=True)
class EntryOutcome:
    allowed: bool
    reason: EntryReason | None
    ticket_id: uuid.UUID | None
    holder_user_id: uuid.UUID | None
    scanned_at: datetime


@dataclass(frozen=True)
class EntryStats:
    event_id: uuid.UUID
    since: datetime
    total_issued: int
    total_entered: int
    total_remaining: int
    rejections_by_reason: dict[str, int] = _field(default_factory=lambda: {})
    last_scan_at: datetime | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "event_id": str(self.event_id),
            "since": self.since.isoformat(),
            "total_issued": self.total_issued,
            "total_entered": self.total_entered,
            "total_remaining": self.total_remaining,
            "rejections_by_reason": dict(self.rejections_by_reason),
            "last_scan_at": self.last_scan_at.isoformat()
            if self.last_scan_at
            else None,
        }
