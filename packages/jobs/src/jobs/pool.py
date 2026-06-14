from arq import create_pool
from arq.connections import ArqRedis, RedisSettings


class _PoolState:
    pool: ArqRedis | None = None


async def get_pool(redis_settings: RedisSettings) -> ArqRedis:
    """Returns the shared Arq connection pool, initializing it on first access."""
    if _PoolState.pool is None:
        _PoolState.pool = await create_pool(redis_settings)
    return _PoolState.pool


async def close_pool() -> None:
    """Closes and clears the shared Arq connection pool."""
    if _PoolState.pool is not None:
        await _PoolState.pool.aclose()
        _PoolState.pool = None
