from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, enabled=True)


from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from db import create_redis_dependency
from com.qode.qrew.v1.payments.core.config import settings

get_redis = create_redis_dependency(settings.redis_url)
