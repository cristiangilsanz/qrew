"""Organisations with their staff, venues, events and the ticket types on sale."""

from __future__ import annotations

import asyncpg

from ..core import SeedConfig, Timeline
from ..data import Dataset

NAME = "catalog"


async def write(
    conn: asyncpg.Connection, data: Dataset, when: Timeline, cfg: SeedConfig
) -> None:
    for org in data.organisations:
        await conn.execute(
            """
            INSERT INTO catalog.organisations (
                id, slug, name, description, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $5)
            """,
            org.id,
            org.slug,
            org.name,
            org.description,
            when.days(-60),
        )
        for person_key, role in org.members:
            await conn.execute(
                """
                INSERT INTO catalog.organisation_members (
                    organisation_id, user_id, role, joined_at
                )
                VALUES ($1, $2, $3::organisation_role, $4)
                """,
                org.id,
                data.person(person_key).id,
                role,
                when.days(-59),
            )

    for venue in data.venues:
        await conn.execute(
            """
            INSERT INTO catalog.venues (
                id, name, address_line, city, country, latitude, longitude,
                geofence_radius_m, timezone, description, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11)
            """,
            venue.id,
            venue.name,
            venue.address,
            venue.city,
            venue.country,
            venue.latitude,
            venue.longitude,
            venue.radius_m,
            venue.timezone,
            f"{venue.name} in {venue.city}.",
            when.days(-58),
        )

    for event in data.events:
        org = next(o for o in data.organisations if o.key == event.organisation)
        venue = data.venue(event.venue)
        await conn.execute(
            """
            INSERT INTO catalog.events (
                id, organisation_id, venue_id, name, description, image_url, status,
                organiser_name, venue_city, starts_at, ends_at, sale_starts_at,
                sale_ends_at,
                max_tickets_per_user, queue_required, queue_admit_rate_per_minute,
                created_at, updated_at, published_at, started_at, cancelled_at
            ) VALUES (
                $1, $2, $3, $4, $5, NULL, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $16, $17, $18, $19
            )
            """,
            event.id,
            org.id,
            venue.id,
            event.name,
            event.description,
            event.status,
            org.name,
            venue.city,
            event.starts_at(when),
            event.ends_at(when),
            event.sale_starts_at(when),
            event.sale_ends_at(when),
            event.max_per_user,
            event.queue_required,
            event.queue_rate,
            when.days(-50),
            when.days(-40) if event.status != "draft" else None,
            when.hours(event.starts_in_hours) if event.status == "ongoing" else None,
            when.days(-2) if event.status == "cancelled" else None,
        )

        for tier in event.ticket_types:
            await conn.execute(
                """
                INSERT INTO catalog.ticket_types (
                    id, event_id, name, description, capacity, reserved_count,
                    price_cents, currency, position, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'EUR', $8, $9, $9)
                """,
                tier.id(event.key),
                event.id,
                tier.name,
                f"{tier.name} access.",
                tier.capacity,
                tier.reserved,
                tier.price_cents,
                tier.position,
                when.days(-49),
            )
