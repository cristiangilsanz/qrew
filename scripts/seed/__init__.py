"""Fixture loader for the local environment.

The seeder wipes the application rows and writes a catalogue of fixtures that covers
every state the product can reach. Identifiers are derived from a fixed namespace and
timestamps hang off the moment it runs, so two runs leave the database in the same
shape with the deadlines always fresh.
"""

from __future__ import annotations

import asyncpg

from .clock import Timeline
from .config import SeedConfig, load
from .dataset import Dataset, build
from .reset import run as truncate
from .writers import WRITERS

__all__ = ["SeedConfig", "load", "run"]


async def run(*, reset: bool = True, verbose: bool = True) -> None:
    cfg = load()
    data = build()
    when = Timeline()
    conn = await asyncpg.connect(cfg.dsn)
    try:
        async with conn.transaction():
            if reset:
                await truncate(conn)
                _say(verbose, "reset", "every application table truncated")
            for writer in WRITERS:
                await writer.write(conn, data, when, cfg)
                _say(verbose, writer.NAME, "seeded")
    finally:
        await conn.close()
    _report(verbose, data, when)


def _say(verbose: bool, scope: str, message: str) -> None:
    if verbose:
        print(f"  {scope:<10} {message}")


def _report(verbose: bool, data: Dataset, when: Timeline) -> None:
    if not verbose:
        return
    print()
    print(f"  Seeded at {when.now.isoformat(timespec='seconds')}")
    print(f"  {len(data.people)} accounts, password Password1! for all of them")
    for person in data.people:
        role = "admin" if person.admin else "user"
        print(f"    {person.name:<8} {person.email:<20} {role}")
    print(
        f"  {len(data.organisations)} organisations, {len(data.venues)} venues, "
        f"{len(data.events)} events"
    )
    print(
        f"  {len(data.reservations)} reservations, {len(data.tickets)} tickets, "
        f"{len(data.listings)} listings, {len(data.assignments)} assignments"
    )
    print(
        f"  {len(data.payments)} payments, {len(data.queue)} queue entries, "
        f"{len(data.scans)} scans"
    )
