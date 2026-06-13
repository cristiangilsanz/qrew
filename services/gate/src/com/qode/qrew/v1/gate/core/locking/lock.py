import asyncio
import random
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.gate.core.locking.errors import LockUnavailableError
from com.qode.qrew.v1.gate.core.locking.lua import RELEASE_SCRIPT
from com.qode.qrew.v1.gate.settings import settings as _settings

logger = structlog.get_logger(__name__)

_KEY_PREFIX = "lock"


class _ClientState:
    client: aioredis.Redis | None = None  # type: ignore[type-arg]


def _shared_client() -> aioredis.Redis:  # type: ignore[type-arg]
    if _ClientState.client is None:
        _ClientState.client = aioredis.from_url(  # type: ignore[type-arg]
            _settings.redis_url, decode_responses=False
        )
    return _ClientState.client


async def close_locking() -> None:
    if _ClientState.client is not None:
        await _ClientState.client.aclose()
    _ClientState.client = None


def _full_key(key: str) -> str:
    return f"{_KEY_PREFIX}:{key}"


class RedisLock:
    def __init__(
        self,
        key: str,
        *,
        ttl_seconds: float,
        redis_client: aioredis.Redis | None = None,  # type: ignore[type-arg]
    ) -> None:
        self.key = key
        self.ttl_seconds = ttl_seconds
        self.nonce: str | None = None
        self._redis = redis_client or _shared_client()
        self._sha: str | None = None

    async def acquire(self, *, retry_attempts: int, retry_delay_ms: int) -> bool:
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
    ttl_seconds: float | None = None,
    retry_attempts: int | None = None,
    retry_delay_ms: int | None = None,
    redis_client: aioredis.Redis | None = None,  # type: ignore[type-arg]
) -> AsyncGenerator[RedisLock, None]:
    lock = RedisLock(
        key,
        ttl_seconds=ttl_seconds if ttl_seconds is not None else _settings.locking_default_ttl_seconds,
        redis_client=redis_client,
    )
    acquired = await lock.acquire(
        retry_attempts=retry_attempts if retry_attempts is not None else _settings.locking_default_retry_attempts,
        retry_delay_ms=retry_delay_ms if retry_delay_ms is not None else _settings.locking_default_retry_delay_ms,
    )
    if not acquired:
        raise LockUnavailableError(key)
    try:
        yield lock
    finally:
        await lock.release()
