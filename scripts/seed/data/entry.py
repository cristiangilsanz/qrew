# declares the fixture scanners and their scans

from __future__ import annotations

from .models import Scan

SCANNERS = (
    ("gate-c", "Gate C", "venue-c", "member"),
    ("gate-a", "Gate A", "venue-a", "member"),
)

SCANS = (
    Scan(
        key="allowed-admin",
        ticket="redeemed-admin",
        event="event-g",
        scanner="gate-c",
        allowed=True,
        reason=None,
        minutes_ago=24 * 60 + 30,
    ),
    Scan(
        key="denied-admin",
        ticket="scanning-admin",
        event="event-c",
        scanner="gate-c",
        allowed=False,
        reason="geofence",
        minutes_ago=12,
    ),
)
