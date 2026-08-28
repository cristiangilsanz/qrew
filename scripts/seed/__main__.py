# parses the command line and runs the seed or truncate flow

from __future__ import annotations

import argparse
import asyncio

import asyncpg

from . import run
from .core import load, truncate


# parses the command line arguments and runs the requested flow
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the local database with fixtures."
    )
    parser.add_argument(
        "--keep", action="store_true", help="append without wiping the tables"
    )
    parser.add_argument(
        "--truncate", action="store_true", help="only wipe, do not seed"
    )
    parser.add_argument("--quiet", action="store_true", help="only report failures")
    args = parser.parse_args()
    if args.truncate:
        asyncio.run(_truncate(verbose=not args.quiet))
        return
    asyncio.run(run(verbose=not args.quiet))


# truncates every table without reseeding
async def _truncate(*, verbose: bool) -> None:
    conn = await asyncpg.connect(load().dsn)
    try:
        await truncate(conn)
    finally:
        await conn.close()
    if verbose:
        print("  reset      every application table truncated")


if __name__ == "__main__":
    main()
