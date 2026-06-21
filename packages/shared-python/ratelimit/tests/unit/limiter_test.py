from unittest.mock import AsyncMock, MagicMock

import pytest

from ratelimit.errors import RateLimitedError
from ratelimit.limiter import RateLimiter


def _make_limiter(*, fail_open: bool = True) -> tuple[RateLimiter, MagicMock]:
    from redis.asyncio import ResponseError

    redis = MagicMock()
    redis.evalsha = AsyncMock(side_effect=ResponseError("no sha"))
    redis.eval = AsyncMock(return_value=[1, 0])
    redis.script_load = AsyncMock(return_value=None)  # prevents SHA caching
    limiter = RateLimiter(redis, key_prefix="test", fail_open=fail_open)
    return limiter, redis


class TestRateLimiterCheck:
    async def test_allowed_when_lua_returns_1(self) -> None:
        limiter, redis = _make_limiter()
        redis.eval = AsyncMock(return_value=[1, 0])
        decision = await limiter.check("ip:1.2.3.4", limit=10, window_seconds=60)
        assert decision.allowed is True
        assert decision.retry_after_seconds == 0

    async def test_denied_when_lua_returns_0(self) -> None:
        limiter, redis = _make_limiter()
        redis.eval = AsyncMock(return_value=[0, 5000])
        decision = await limiter.check("ip:1.2.3.4", limit=10, window_seconds=60)
        assert decision.allowed is False
        assert decision.retry_after_seconds == 5

    async def test_fail_open_on_redis_error(self) -> None:
        limiter, redis = _make_limiter(fail_open=True)
        from redis.asyncio import RedisError

        redis.eval = AsyncMock(side_effect=RedisError("down"))
        decision = await limiter.check("ip:x", limit=5, window_seconds=10)
        assert decision.allowed is True

    async def test_fail_closed_raises_on_redis_error(self) -> None:
        limiter, redis = _make_limiter(fail_open=False)
        from redis.asyncio import RedisError

        redis.eval = AsyncMock(side_effect=RedisError("down"))
        with pytest.raises(Exception):
            await limiter.check("ip:x", limit=5, window_seconds=10)


class TestCheckMany:
    async def test_passes_when_all_allowed(self) -> None:
        limiter, redis = _make_limiter()
        redis.eval = AsyncMock(return_value=[1, 0])
        await limiter.check_many([
            ("ip:1.2.3.4", 100, 60),
            ("user:abc", 50, 60),
        ])

    async def test_raises_when_any_denied(self) -> None:
        limiter, redis = _make_limiter()
        redis.eval = AsyncMock(return_value=[0, 3000])
        with pytest.raises(RateLimitedError):
            await limiter.check_many([("ip:1.2.3.4", 10, 60)])

    async def test_raises_worst_retry_after(self) -> None:
        limiter, redis = _make_limiter()
        call_count = 0

        async def _eval(*args: object, **kwargs: object) -> list[int]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [0, 2000]
            return [0, 10000]

        redis.eval = AsyncMock(side_effect=_eval)
        with pytest.raises(RateLimitedError) as exc_info:
            await limiter.check_many([
                ("key1", 10, 60),
                ("key2", 10, 60),
            ])
        assert exc_info.value.retry_after_seconds == 10
