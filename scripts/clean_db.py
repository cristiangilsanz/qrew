#!/usr/bin/env python3
"""Wipe all application data from the database (preserves schema/migrations)."""

import asyncio
from pathlib import Path

import asyncpg
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
IDENTITY_CFG = REPO_ROOT / "apps/api/services/identity/config/local.yaml"


async def clean() -> None:
    cfg = yaml.safe_load(IDENTITY_CFG.read_text())
    db_url = cfg["database_url"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
            TRUNCATE
                ticketing.tickets,
                ticketing.event_venue_context,
                ticketing.device_context,
                sales.reservation_holders,
                sales.reservations,
                sales.event_context,
                sales.ticket_type_inventory,
                sales.user_age_context,
                sales.fingerprint_context,
                catalog.ticket_types,
                catalog.events,
                catalog.organisation_members,
                catalog.venues,
                catalog.organisations,
                identity.users
            CASCADE
        """)
    finally:
        await conn.close()
    print("Database cleaned.")


if __name__ == "__main__":
    asyncio.run(clean())
