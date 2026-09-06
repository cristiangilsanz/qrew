# shares a single arq connection pool across every job enqueue call
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings


class _PoolState:
    pool: ArqRedis | None = None


# builds the shared arq pool the first time it is needed
async def get_pool(redis_settings: RedisSettings) -> ArqRedis:
    if _PoolState.pool is None:
        _PoolState.pool = await create_pool(redis_settings)
    return _PoolState.pool


# closes the shared arq pool
async def close_pool() -> None:
    if _PoolState.pool is not None:
        await _PoolState.pool.aclose()
        _PoolState.pool = None
