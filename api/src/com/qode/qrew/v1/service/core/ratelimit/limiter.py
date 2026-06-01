import math
import time
import uuid
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.service.core.ratelimit.errors import RateLimitedError
from com.qode.qrew.v1.service.core.ratelimit.lua_script import LUA_SCRIPT
from com.qode.qrew.v1.service.settings import settings as _settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after_seconds: int


class RateLimiter:
    """Atomic sliding-window rate limiter backed by Redis and a Lua script."""

    def __init__(
        self,
        redis_client: aioredis.Redis,  # type: ignore[type-arg]
        *,
        key_prefix: str = "ratelimit",
        fail_open: bool | None = None,
    ) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._fail_open = (
            _settings.ratelimit_fail_open if fail_open is None else fail_open
        )
        self._sha: str | None = None

    def _full_key(self, scope_key: str) -> str:
        return f"{self._key_prefix}:{scope_key}"

    async def _evaluate(
        self,
        full_key: str,
        now_ms: int,
        window_ms: int,
        limit: int,
        member: str,
    ) -> list[int]:
        args: list[Any] = [1, full_key, now_ms, window_ms, limit, member]
        if self._sha is not None:
            try:
                return await self._redis.evalsha(self._sha, *args)  # type: ignore[misc,no-any-return]
            except aioredis.ResponseError:
                self._sha = None
        raw = await self._redis.eval(LUA_SCRIPT, *args)  # type: ignore[misc]
        try:
            self._sha = await self._redis.script_load(LUA_SCRIPT)  # type: ignore[misc]
        except aioredis.RedisError:
            self._sha = None
        return raw  # type: ignore[no-any-return]

    async def check(self, scope_key: str, limit: int, window_seconds: int) -> Decision:
        """Record an attempt and return whether it is allowed."""
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        member = f"{now_ms}-{uuid.uuid4().hex}"
        try:
            raw = await self._evaluate(
                self._full_key(scope_key), now_ms, window_ms, limit, member
            )
        except aioredis.RedisError as exc:
            if self._fail_open:
                await logger.awarning(
                    "ratelimit_redis_unavailable",
                    error=repr(exc),
                    scope=scope_key,
                )
                return Decision(allowed=True, retry_after_seconds=0)
            raise
        allowed_flag, retry_after_ms = int(raw[0]), int(raw[1])
        retry_after_s = math.ceil(retry_after_ms / 1000) if retry_after_ms > 0 else 0
        return Decision(allowed=bool(allowed_flag), retry_after_seconds=retry_after_s)

    async def check_many(self, checks: list[tuple[str, int, int]]) -> None:
        """Apply many scope checks; raise on the first that fails."""
        worst: RateLimitedError | None = None
        for scope_key, limit, window_seconds in checks:
            decision = await self.check(scope_key, limit, window_seconds)
            if decision.allowed:
                continue
            err = RateLimitedError(
                scope=scope_key,
                limit=limit,
                window_seconds=window_seconds,
                retry_after_seconds=decision.retry_after_seconds,
            )
            if worst is None or err.retry_after_seconds > worst.retry_after_seconds:
                worst = err
        if worst is not None:
            raise worst
