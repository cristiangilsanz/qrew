import pytest_asyncio
from sqlalchemy import text

from com.qode.qrew.v1.service.core.infra.database import engine


@pytest_asyncio.fixture(autouse=True)
async def clean_db() -> None:
    """Dispose stale pool connections"""
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE audit_events, passkey_credentials, users"
                " RESTART IDENTITY CASCADE"
            )
        )
