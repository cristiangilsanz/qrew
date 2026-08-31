# truncates every seeded table in dependency order before a fresh load

from __future__ import annotations

import asyncpg

TABLES = (
    "entry.scans",
    "entry.ticket_contexts",
    "entry.scanners",
    "payments.payments",
    "ticketing.tickets",
    "ticketing.event_venue_context",
    "ticketing.device_context",
    "sales.market_assignments",
    "sales.market_listings",
    "sales.market_queue_entries",
    "sales.reservation_holders",
    "sales.reservation_items",
    "sales.reservations",
    "sales.event_context",
    "sales.ticket_type_inventory",
    "sales.user_age_context",
    "sales.fingerprint_context",
    "catalog.ticket_types",
    "catalog.events",
    "catalog.organisation_members",
    "catalog.venues",
    "catalog.organisations",
    "identity.passkey_credentials",
    "identity.device_fingerprints",
    "identity.sessions",
    "identity.notifications",
    "identity.outbox",
    "identity.devices",
    "identity.users",
    "audit.audit_events",
)


# truncates every seeded table
async def run(conn: asyncpg.Connection) -> None:
    await conn.execute(f"TRUNCATE {', '.join(TABLES)} CASCADE")
