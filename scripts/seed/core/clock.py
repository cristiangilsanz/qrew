# anchors every fixture's timestamp to the moment the script runs

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Timeline:
    now: datetime = field(default_factory=lambda: datetime.now(UTC))

    # offsets the anchor time by a number of minutes
    def minutes(self, value: float) -> datetime:
        return self.now + timedelta(minutes=value)

    # offsets the anchor time by a number of hours
    def hours(self, value: float) -> datetime:
        return self.now + timedelta(hours=value)

    # offsets the anchor time by a number of days
    def days(self, value: float) -> datetime:
        return self.now + timedelta(days=value)
