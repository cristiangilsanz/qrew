from unittest.mock import AsyncMock, MagicMock

import pytest

from locking.errors import LockUnavailableError
from locking.lock import RedisLock, redlock


def _make_redis(*, set_returns: object = True) -> MagicMock:
    redis = MagicMock()
    redis.set = AsyncMock(return_value=set_returns)
    redis.eval = AsyncMock(return_value=None)
    redis.evalsha = AsyncMock(side_effect=Exception("no sha"))
    redis.script_load = AsyncMock(return_value="sha123")
    return redis


class TestRedisLockAcquire:
    async def test_acquire_succeeds(self) -> None:
        redis = _make_redis(set_returns=True)
        lock = RedisLock("mykey", ttl_seconds=10.0, redis_client=redis)
        acquired = await lock.acquire(retry_attempts=0, retry_delay_ms=0)
        assert acquired is True
        assert lock.nonce is not None

    async def test_acquire_fails_when_redis_returns_none(self) -> None:
        redis = _make_redis(set_returns=None)
        lock = RedisLock("mykey", ttl_seconds=10.0, redis_client=redis)
        acquired = await lock.acquire(retry_attempts=0, retry_delay_ms=0)
        assert acquired is False
        assert lock.nonce is None

    async def test_acquire_retries_on_failure(self) -> None:
        redis = _make_redis()
        call_count = 0

        async def _set(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return True if call_count == 2 else None

        redis.set = AsyncMock(side_effect=_set)
        lock = RedisLock("mykey", ttl_seconds=5.0, redis_client=redis)
        acquired = await lock.acquire(retry_attempts=2, retry_delay_ms=0)
        assert acquired is True
        assert call_count == 2


class TestRedisLockRelease:
    async def test_release_without_acquire_is_noop(self) -> None:
        redis = _make_redis()
        lock = RedisLock("mykey", ttl_seconds=5.0, redis_client=redis)
        await lock.release()
        redis.eval.assert_not_awaited()

    async def test_release_clears_nonce(self) -> None:
        redis = _make_redis(set_returns=True)
        lock = RedisLock("mykey", ttl_seconds=5.0, redis_client=redis)
        await lock.acquire(retry_attempts=0, retry_delay_ms=0)
        assert lock.nonce is not None
        await lock.release()
        assert lock.nonce is None

    async def test_release_redis_error_is_swallowed(self) -> None:
        from redis.asyncio import RedisError

        redis = _make_redis(set_returns=True)
        redis.eval = AsyncMock(side_effect=RedisError("down"))
        lock = RedisLock("mykey", ttl_seconds=5.0, redis_client=redis)
        await lock.acquire(retry_attempts=0, retry_delay_ms=0)
        await lock.release()
        assert lock.nonce is None


class TestRedlock:
    async def test_context_manager_acquires_and_releases(self) -> None:
        redis = _make_redis(set_returns=True)
        async with redlock(
            "testkey",
            redis_url="redis://localhost",
            ttl_seconds=5.0,
            retry_attempts=0,
            redis_client=redis,
        ) as lock:
            assert lock.nonce is not None
        assert lock.nonce is None

    async def test_raises_when_lock_unavailable(self) -> None:
        redis = _make_redis(set_returns=None)
        with pytest.raises(LockUnavailableError) as exc_info:
            async with redlock(
                "busykey",
                redis_url="redis://localhost",
                ttl_seconds=5.0,
                retry_attempts=0,
                redis_client=redis,
            ):
                pass
        assert "busykey" in str(exc_info.value)


class TestLockUnavailableError:
    def test_message_includes_key(self) -> None:
        err = LockUnavailableError("my-resource")
        assert "my-resource" in str(err)
        assert err.key == "my-resource"
