from collections.abc import AsyncGenerator
from urllib.parse import urlparse

import redis.asyncio as aioredis
from arq.connections import RedisSettings

from com.qode.qrew.v1.catalog.settings import settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    try:
        yield client
    finally:
        await client.aclose()


def redis_settings_from_url(url: str | None = None) -> RedisSettings:
    parsed = urlparse(url or settings.redis_url)
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
