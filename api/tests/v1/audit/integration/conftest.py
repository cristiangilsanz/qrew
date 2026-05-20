from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.database import AsyncSessionLocal, engine


@pytest_asyncio.fixture(autouse=True)
async def clean_db() -> None:
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE audit_events, passkey_credentials, users"
                " RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
