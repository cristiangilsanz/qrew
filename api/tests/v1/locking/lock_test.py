import asyncio
from typing import Any

import fakeredis.aioredis
import pytest

from com.qode.qrew.v1.service.core.locking import (
    LockUnavailableError,
    RedisLock,
    redlock,
)


@pytest.fixture
def redis_client() -> Any:
    return fakeredis.aioredis.FakeRedis()


async def test_acquire_succeeds_first_then_blocks(redis_client: Any) -> None:
    first = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    second = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    assert await first.acquire(retry_attempts=0, retry_delay_ms=10) is True
    assert await second.acquire(retry_attempts=0, retry_delay_ms=10) is False
    await first.release()


async def test_release_only_deletes_own_lock(redis_client: Any) -> None:
    """The canonical Redlock footgun: a stalled holder must not release others."""
    a = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    await a.acquire(retry_attempts=0, retry_delay_ms=10)
    await a.release()

    b = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    await b.acquire(retry_attempts=0, retry_delay_ms=10)

    # A's nonce was cleared after release; calling release again is a no-op.
    await a.release()

    # B's lock still holds.
    c = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    assert await c.acquire(retry_attempts=0, retry_delay_ms=10) is False
    await b.release()


async def test_zombie_release_does_not_drop_new_holder(redis_client: Any) -> None:
    """A holder whose TTL expired must not release a successor's lock."""
    a = RedisLock("k", ttl_seconds=0.1, redis_client=redis_client)
    await a.acquire(retry_attempts=0, retry_delay_ms=10)

    await asyncio.sleep(0.2)

    b = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    assert await b.acquire(retry_attempts=0, retry_delay_ms=10) is True

    # Late release attempt by A must NOT remove B's lock.
    await a.release()

    c = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    assert await c.acquire(retry_attempts=0, retry_delay_ms=10) is False
    await b.release()


async def test_concurrent_acquire_yields_single_holder(redis_client: Any) -> None:
    async def attempt() -> bool:
        lock = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
        ok = await lock.acquire(retry_attempts=0, retry_delay_ms=5)
        return ok

    results = await asyncio.gather(*[attempt() for _ in range(20)])
    assert sum(1 for ok in results if ok) == 1


async def test_redlock_context_manager_acquires_and_releases(redis_client: Any) -> None:
    async with redlock(
        "k",
        ttl_seconds=5,
        retry_attempts=0,
        retry_delay_ms=10,
        redis_client=redis_client,
    ):
        already = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
        assert await already.acquire(retry_attempts=0, retry_delay_ms=10) is False
    after = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    assert await after.acquire(retry_attempts=0, retry_delay_ms=10) is True
    await after.release()


async def test_redlock_raises_when_budget_exhausted(redis_client: Any) -> None:
    holder = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    await holder.acquire(retry_attempts=0, retry_delay_ms=10)
    with pytest.raises(LockUnavailableError) as info:
        async with redlock(
            "k",
            ttl_seconds=5,
            retry_attempts=2,
            retry_delay_ms=5,
            redis_client=redis_client,
        ):
            pass
    assert info.value.key == "k"
    await holder.release()


async def test_release_recovers_from_noscript(redis_client: Any) -> None:
    lock = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    await lock.acquire(retry_attempts=0, retry_delay_ms=10)
    # Force the next release to take the eval+script_load fallback path
    lock._sha = "deadbeef" * 5  # pyright: ignore[reportPrivateUsage]
    await lock.release()
    after = RedisLock("k", ttl_seconds=5, redis_client=redis_client)
    assert await after.acquire(retry_attempts=0, retry_delay_ms=10) is True
    await after.release()
