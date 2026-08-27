"""Gate scanners, the ticket projection they read and a couple of past scans."""

from __future__ import annotations

import asyncpg

from ..clock import Timeline
from ..config import SeedConfig
from ..dataset import Dataset
from ..ids import ident

NAME = "entry"

_SCANNERS = (
    ("gate-c", "Gate C", "venue-c", "member"),
    ("gate-a", "Gate A", "venue-a", "member"),
)
_SCANNABLE = {"issued", "scanning", "redeemed"}


async def write(
    conn: asyncpg.Connection, data: Dataset, when: Timeline, cfg: SeedConfig
) -> None:
    for key, name, venue_key, owner_key in _SCANNERS:
        await conn.execute(
            """
            INSERT INTO entry.scanners (
                id, name, venue_id, created_by, created_at, is_active
            )
            VALUES ($1, $2, $3, $4, $5, TRUE)
            """,
            ident("scanner", key),
            name,
            data.venue(venue_key).id,
            data.person(owner_key).id,
            when.days(-10),
        )

    for ticket in data.tickets:
        if ticket.state not in _SCANNABLE:
            continue
        event = data.event(ticket.event)
        await conn.execute(
            """
            INSERT INTO entry.ticket_contexts (ticket_id, event_id, venue_id,
            owner_user_id,
                                               bound_device_id, state, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            ticket.id,
            event.id,
            data.venue(event.venue).id,
            data.person(ticket.user).id,
            ident("device", ticket.bound_device) if ticket.bound_device else None,
            ticket.state,
            when.hours(-1),
        )

    for scan in data.scans:
        await conn.execute(
            """
            INSERT INTO entry.scans (id, event_id, ticket_id, scanner_id, allowed,
            reason,
                                     scanned_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            scan.id,
            data.event(scan.event).id,
            data.ticket(scan.ticket).id,
            ident("scanner", scan.scanner),
            scan.allowed,
            scan.reason,
            when.minutes(-scan.minutes_ago),
        )
