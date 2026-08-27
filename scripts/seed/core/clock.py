"""Every timestamp hangs off the moment the seeder runs, never off a fixed date."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Timeline:
    now: datetime = field(default_factory=lambda: datetime.now(UTC))

    def minutes(self, value: float) -> datetime:
        return self.now + timedelta(minutes=value)

    def hours(self, value: float) -> datetime:
        return self.now + timedelta(hours=value)

    def days(self, value: float) -> datetime:
        return self.now + timedelta(days=value)
