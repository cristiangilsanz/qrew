from db import create_redis_dependency
from slowapi import Limiter
from slowapi.util import get_remote_address

from com.qode.qrew.v1.entry.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)

get_redis = create_redis_dependency(settings.redis_url)
