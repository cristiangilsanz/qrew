from urllib.parse import urlparse

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from com.qode.qrew.v1.service.settings import settings


def redis_settings_from_url(url: str | None = None) -> RedisSettings:
    """Build an arq RedisSettings from settings.redis_url (or an override)."""
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


class _PoolState:
    pool: ArqRedis | None = None


async def get_pool() -> ArqRedis:
    """Return a process-wide ArqRedis pool, creating it lazily."""
    if _PoolState.pool is None:
        _PoolState.pool = await create_pool(redis_settings_from_url())
    return _PoolState.pool


async def close_pool() -> None:
    if _PoolState.pool is not None:
        await _PoolState.pool.aclose()
        _PoolState.pool = None
