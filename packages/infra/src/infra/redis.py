from collections.abc import AsyncGenerator
from urllib.parse import urlparse

import redis.asyncio as aioredis
from arq.connections import RedisSettings


def create_redis_dependency(redis_url: str):
    """Creates a FastAPI dependency that yields a Redis client per request."""

    async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
        client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
            redis_url, decode_responses=False
        )
        try:
            yield client
        finally:
            await client.aclose()

    return get_redis


def redis_settings_from_url(url: str) -> RedisSettings:
    """Parses a Redis connection URL into Arq-compatible connection settings."""
    parsed = urlparse(url)
    database = 0
    if parsed.path and parsed.path != "/":
        database = int(parsed.path.lstrip("/"))
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        username=parsed.username,
        password=parsed.password,
        ssl=parsed.scheme == "rediss",
    )
