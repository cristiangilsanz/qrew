# truncates and reseeds the local database from the fixture dataset

from __future__ import annotations

import asyncpg

from .core import SeedConfig, Timeline, load, truncate
from .data import Dataset, build, build_accounts
from .writers import WRITERS, identity

__all__ = ["SeedConfig", "load", "run"]


# truncates every table then writes each service's fixtures in order
async def run(*, verbose: bool = True, accounts_only: bool = False) -> None:
    cfg = load()
    data = build_accounts() if accounts_only else build()
    writers = (identity,) if accounts_only else WRITERS
    when = Timeline()
    conn = await asyncpg.connect(cfg.dsn)
    try:
        async with conn.transaction():
            await truncate(conn)
            _say(verbose, "reset", "every application table truncated")
            for writer in writers:
                await writer.write(conn, data, when, cfg)
                _say(verbose, writer.NAME, "seeded")
    finally:
        await conn.close()
    _report(verbose, data, when)


# prints a progress line when verbose reporting is on
def _say(verbose: bool, scope: str, message: str) -> None:
    if verbose:
        print(f"  {scope:<10} {message}")


# prints a summary of every fixture the run seeded
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
