from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from com.qode.qrew.v1.gate.settings import settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    try:
        yield client
    finally:
        await client.aclose()
