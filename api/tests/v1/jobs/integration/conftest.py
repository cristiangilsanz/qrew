import pytest_asyncio
from sqlalchemy import text

from com.qode.qrew.v1.service.core.infra.database import engine


@pytest_asyncio.fixture(autouse=True)
async def clean_db() -> None:
    """Dispose stale pool connections then truncate all tables.

    pytest-asyncio creates a new event loop per test. The module-level engine
    holds connections from the previous loop, which causes "attached to a
    different loop" errors. Disposing before each test forces the pool to open
    fresh connections on the current loop.
    """
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE audit_events, passkey_credentials, users"
                " RESTART IDENTITY CASCADE"
            )
        )
