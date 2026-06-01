import asyncio
from typing import Any

import fakeredis.aioredis
import pytest
import redis.asyncio as aioredis

from com.qode.qrew.v1.service.core.ratelimit import (
    RateLimitedError,
    RateLimiter,
)


@pytest.fixture
def redis_client() -> Any:
    return fakeredis.aioredis.FakeRedis()


async def test_under_limit_allowed(redis_client: Any) -> None:
    limiter = RateLimiter(redis_client)
    for _ in range(3):
        decision = await limiter.check("user:abc", limit=5, window_seconds=60)
        assert decision.allowed is True


async def test_over_limit_rejected(redis_client: Any) -> None:
    limiter = RateLimiter(redis_client)
    for _ in range(5):
        decision = await limiter.check("user:abc", limit=5, window_seconds=60)
        assert decision.allowed is True
    decision = await limiter.check("user:abc", limit=5, window_seconds=60)
    assert decision.allowed is False
    assert decision.retry_after_seconds >= 1


async def test_window_slides_releases_capacity(redis_client: Any) -> None:
    limiter = RateLimiter(redis_client, fail_open=False)
    for _ in range(2):
        await limiter.check("user:slide", limit=2, window_seconds=1)
    decision = await limiter.check("user:slide", limit=2, window_seconds=1)
    assert decision.allowed is False
    await asyncio.sleep(1.1)
    decision = await limiter.check("user:slide", limit=2, window_seconds=1)
    assert decision.allowed is True


async def test_check_many_raises_on_first_failure(redis_client: Any) -> None:
    limiter = RateLimiter(redis_client)
    for _ in range(3):
        await limiter.check("ip:1.1.1.1", limit=3, window_seconds=60)
    with pytest.raises(RateLimitedError) as info:
        await limiter.check_many(
            [
                ("ip:1.1.1.1", 3, 60),
                ("user:xyz", 100, 60),
            ]
        )
    assert info.value.scope == "ip:1.1.1.1"


async def test_concurrent_requests_respect_limit(redis_client: Any) -> None:
    limiter = RateLimiter(redis_client)
    results = await asyncio.gather(
        *[limiter.check("ip:race", limit=10, window_seconds=60) for _ in range(50)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 10


async def test_fail_open_when_redis_errors() -> None:
    class _Broken:
        async def script_load(self, _script: str) -> str:
            raise aioredis.RedisError("down")

        async def evalsha(self, *_args: Any, **_kwargs: Any) -> Any:
            raise aioredis.RedisError("down")

        async def eval(self, *_args: Any, **_kwargs: Any) -> Any:
            raise aioredis.RedisError("down")

    limiter = RateLimiter(_Broken(), fail_open=True)  # type: ignore[arg-type]
    decision = await limiter.check("any", limit=1, window_seconds=60)
    assert decision.allowed is True
