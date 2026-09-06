# builds a redis client dependency and arq settings from a connection url
from collections.abc import AsyncGenerator, Callable
from urllib.parse import urlparse

import redis.asyncio as aioredis
from arq.connections import RedisSettings


# builds a fastapi dependency that yields a redis client per request
def create_redis_dependency(
    redis_url: str,
) -> Callable[[], AsyncGenerator[aioredis.Redis, None]]:

    # yields a redis client for the duration of a request
    async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
        client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
            redis_url, decode_responses=False
        )
        try:
            yield client
        finally:
            await client.aclose()

    return get_redis


# parses a redis url into arq's connection settings
def redis_settings_from_url(url: str) -> RedisSettings:
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
