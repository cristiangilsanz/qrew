from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from slowapi import Limiter
from slowapi.util import get_remote_address

from com.qode.qrew.v1.sales.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
        settings.redis_url, decode_responses=False
    )
    try:
        yield client
    finally:
        await client.aclose()
