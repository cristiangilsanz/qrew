import asyncio
import random
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
import structlog

from infra.locking.errors import LockUnavailableError
from infra.locking.lua import RELEASE_SCRIPT

logger = structlog.get_logger(__name__)

_KEY_PREFIX = "lock"


class _ClientState:
    client: aioredis.Redis | None = None  # type: ignore[type-arg]
    url: str | None = None


def _shared_client(redis_url: str) -> aioredis.Redis:  # type: ignore[type-arg]
    if _ClientState.client is None or _ClientState.url != redis_url:
        _ClientState.url = redis_url
        _ClientState.client = aioredis.from_url(  # type: ignore[type-arg]
            redis_url, decode_responses=False
        )
    return _ClientState.client


async def close_locking() -> None:
    """Closes the shared Redis client used for distributed locking."""
    if _ClientState.client is not None:
        await _ClientState.client.aclose()
    _ClientState.client = None
    _ClientState.url = None


def _full_key(key: str) -> str:
    return f"{_KEY_PREFIX}:{key}"


class RedisLock:
    """Manages a single acquire-and-release cycle for a Redis-backed distributed mutex."""

    def __init__(
        self,
        key: str,
        *,
        ttl_seconds: float,
        redis_client: aioredis.Redis,  # type: ignore[type-arg]
    ) -> None:
        self.key = key
        self.ttl_seconds = ttl_seconds
        self.nonce: str | None = None
        self._redis = redis_client
        self._sha: str | None = None

    async def acquire(self, *, retry_attempts: int, retry_delay_ms: int) -> bool:
        """Attempts to acquire the lock with jittered retries up to the configured limit."""
        nonce = uuid.uuid4().hex
        ttl_ms = int(self.ttl_seconds * 1000)
        for attempt in range(retry_attempts + 1):
            acquired = await self._redis.set(  # type: ignore[misc]
                _full_key(self.key), nonce.encode(), px=ttl_ms, nx=True
            )
            if acquired:
                self.nonce = nonce
                return True
            if attempt >= retry_attempts:
                return False
            await asyncio.sleep(random.uniform(0, retry_delay_ms) / 1000)
        return False

    async def release(self) -> None:
        """Releases the lock only when the current ownership token still matches."""
        if self.nonce is None:
            return
        try:
            await self._eval_release()
        except aioredis.RedisError as exc:
            await logger.awarning("lock_release_failed", key=self.key, error=repr(exc))
        finally:
            self.nonce = None

    async def _eval_release(self) -> None:
        full = _full_key(self.key)
        nonce = (self.nonce or "").encode()
        if self._sha is not None:
            try:
                await self._redis.evalsha(self._sha, 1, full, nonce)  # type: ignore[misc]
                return
            except aioredis.ResponseError:
                self._sha = None
        await self._redis.eval(RELEASE_SCRIPT, 1, full, nonce)  # type: ignore[misc]
        try:
            loaded: Any = await self._redis.script_load(RELEASE_SCRIPT)  # type: ignore[misc]
            self._sha = loaded if isinstance(loaded, str) else None
        except aioredis.RedisError:
            self._sha = None


@asynccontextmanager
async def redlock(
    key: str,
    *,
    redis_url: str,
    ttl_seconds: float = 30.0,
    retry_attempts: int = 3,
    retry_delay_ms: int = 200,
    redis_client: aioredis.Redis | None = None,  # type: ignore[type-arg]
) -> AsyncGenerator[RedisLock, None]:
    """Acquires a distributed Redis mutex and releases it when the context exits."""
    lock = RedisLock(
        key,
        ttl_seconds=ttl_seconds,
        redis_client=redis_client or _shared_client(redis_url),
    )
    acquired = await lock.acquire(
        retry_attempts=retry_attempts,
        retry_delay_ms=retry_delay_ms,
    )
    if not acquired:
        raise LockUnavailableError(key)
    try:
        yield lock
    finally:
        await lock.release()
