from typing import Any

import fakeredis.aioredis
import pytest

from com.qode.qrew.v1.service.core.idempotency import (
    IdempotencyStore,
    StoredResponse,
)


@pytest.fixture
def redis_client() -> Any:
    return fakeredis.aioredis.FakeRedis()


def _stored(fingerprint: str = "fp-1") -> StoredResponse:
    return StoredResponse(
        status_code=201,
        headers={"content-type": "application/json"},
        body=b'{"id": "abc"}',
        fingerprint=fingerprint,
    )


async def test_first_acquire_returns_lock_and_no_cache(redis_client: Any) -> None:
    store = IdempotencyStore(redis_client, lock_seconds=60)
    result = await store.acquire("global", None, "k1")
    assert result.acquired is True
    assert result.cached is None


async def test_save_persists_response_for_replay(redis_client: Any) -> None:
    store = IdempotencyStore(redis_client, lock_seconds=60)
    await store.acquire("global", None, "k1")
    await store.save("global", None, "k1", _stored(), ttl_seconds=300)
    cached = await store.fetch("global", None, "k1")
    assert cached is not None
    assert cached.status_code == 201
    assert cached.fingerprint == "fp-1"


async def test_second_acquire_with_cached_returns_lock_plus_cached(
    redis_client: Any,
) -> None:
    store = IdempotencyStore(redis_client, lock_seconds=60)
    await store.acquire("global", None, "k1")
    await store.save("global", None, "k1", _stored(), ttl_seconds=300)
    result = await store.acquire("global", None, "k1")
    assert result.cached is not None
    assert result.cached.fingerprint == "fp-1"


async def test_concurrent_second_acquire_loses_lock_no_cache(
    redis_client: Any,
) -> None:
    store = IdempotencyStore(redis_client, lock_seconds=60)
    first = await store.acquire("global", None, "k1")
    assert first.acquired is True
    second = await store.acquire("global", None, "k1")
    assert second.acquired is False
    assert second.cached is None


async def test_release_frees_the_lock(redis_client: Any) -> None:
    store = IdempotencyStore(redis_client, lock_seconds=60)
    await store.acquire("global", None, "k1")
    await store.release("global", None, "k1")
    again = await store.acquire("global", None, "k1")
    assert again.acquired is True


async def test_scopes_partition_keys(redis_client: Any) -> None:
    store = IdempotencyStore(redis_client, lock_seconds=60)
    await store.acquire("user", "u1", "shared")
    other = await store.acquire("user", "u2", "shared")
    assert other.acquired is True
    global_one = await store.acquire("global", None, "shared")
    assert global_one.acquired is True
