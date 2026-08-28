# writes the fixture event and device context and tickets into ticketing

from __future__ import annotations

import asyncpg

from ..core import SeedConfig, Timeline, ident
from ..data import Dataset

NAME = "ticketing"


# inserts every ticketing fixture row
async def write(
    conn: asyncpg.Connection, data: Dataset, when: Timeline, cfg: SeedConfig
) -> None:
    for event in data.events:
        venue = data.venue(event.venue)
        await conn.execute(
            """
            INSERT INTO ticketing.event_venue_context (
                event_id, venue_id, event_status, starts_at, ends_at, latitude,
                longitude,
                geofence_radius_m, timezone, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            event.id,
            venue.id,
            event.status,
            event.starts_at(when),
            event.ends_at(when),
            venue.latitude,
            venue.longitude,
            venue.radius_m,
            venue.timezone,
            when.now,
        )

    for person_key, _ in data.devices:
        await conn.execute(
            """
            INSERT INTO ticketing.device_context (device_id, user_id, attested_at,
                                                  revoked_at, updated_at)
            VALUES ($1, $2, $3, NULL, $4)
            """,
            ident("device", person_key),
            data.person(person_key).id,
            when.days(-20),
            when.now,
        )

    for ticket in data.tickets:
        event = data.event(ticket.event)
        tier = data.ticket_type(ticket.event, ticket.ticket_type)
        reservation = (
            next(r for r in data.reservations if r.key == ticket.reservation).id
            if ticket.reservation
            else None
        )
        await conn.execute(
            """
            INSERT INTO ticketing.tickets (
                id, reservation_id, event_id, ticket_type_id, owner_user_id,
                bound_device_id,
                state, state_updated_at, issued_at, expired_at, holder_name, holder_dni,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $9, $8)
            """,
            ticket.id,
            reservation,
            event.id,
            tier.id(event.key),
            data.person(ticket.user).id,
            ident("device", ticket.bound_device) if ticket.bound_device else None,
            ticket.state,
            when.hours(-1),
            when.hours(-ticket.issued_hours_ago),
            when.hours(-ticket.expired_hours_ago) if ticket.expired_hours_ago else None,
            ticket.holder_name,
            ticket.holder_dni,
        )
