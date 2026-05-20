from collections.abc import AsyncGenerator

import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.database import AsyncSessionLocal, engine
from com.qode.qrew.v1.service.core.limiter import limiter
from com.qode.qrew.v1.service.core.redis import get_redis
from com.qode.qrew.v1.service.main import app

_TEST_REDIS_URL = "redis://localhost:6379/1"


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


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a live DB session for direct assertions on persisted state."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def redis_test() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    """Yield a Redis client on DB 1, flushed before and after each test."""
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        _TEST_REDIS_URL, decode_responses=False
    )
    await client.flushdb()  # type: ignore[reportUnknownMemberType]
    try:
        yield client
    finally:
        await client.flushdb()  # type: ignore[reportUnknownMemberType]
        await client.aclose()


@pytest_asyncio.fixture
async def client(redis_test: aioredis.Redis) -> AsyncGenerator[AsyncClient, None]:  # type: ignore[type-arg]
    """ASGI test client with Redis overridden to the isolated test DB."""

    async def _get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
        yield redis_test

    app.dependency_overrides[get_redis] = _get_redis
    limiter.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_redis, None)
