# stores and locks idempotent responses in redis
import base64
import json
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis
import structlog

from .decorator import DEFAULT_HEADER_BLACKLIST

logger = structlog.get_logger(__name__)

_RESULT_PREFIX = "idem:result"
_LOCK_PREFIX = "idem:lock"


@dataclass(frozen=True)
class StoredResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    fingerprint: str


@dataclass(frozen=True)
class LockResult:
    acquired: bool
    cached: StoredResponse | None


# builds the redis key prefix for a scope
def _scope_prefix(scope: str, user_id: str | None) -> str:
    if scope == "user":
        return f"u:{user_id}" if user_id else "u:anon"
    return "g"


# builds the redis key that stores a cached response
def _result_key(scope: str, user_id: str | None, key: str) -> str:
    return f"{_RESULT_PREFIX}:{_scope_prefix(scope, user_id)}:{key}"


# builds the redis key that locks a request in flight
def _lock_key(scope: str, user_id: str | None, key: str) -> str:
    return f"{_LOCK_PREFIX}:{_scope_prefix(scope, user_id)}:{key}"


# serializes a stored response for redis
def _serialise(response: StoredResponse) -> str:
    return json.dumps(
        {
            "status_code": response.status_code,
            "headers": response.headers,
            "body_b64": base64.b64encode(response.body).decode(),
            "fingerprint": response.fingerprint,
        }
    )


# deserializes a stored response from redis
def _deserialise(raw: bytes | str) -> StoredResponse:
    payload = json.loads(raw)
    return StoredResponse(
        status_code=int(payload["status_code"]),
        headers=dict(payload["headers"]),
        body=base64.b64decode(payload["body_b64"]),
        fingerprint=str(payload["fingerprint"]),
    )


class IdempotencyStore:
    # stores the redis client and lock ttl the store uses
    def __init__(
        self,
        redis_client: aioredis.Redis,  # type: ignore[type-arg]
        *,
        lock_seconds: int,
    ) -> None:
        self._redis = redis_client
        self._lock_seconds = lock_seconds

    # locks a request in flight and returns any already cached response
    async def acquire(self, scope: str, user_id: str | None, key: str) -> LockResult:
        lock_key = _lock_key(scope, user_id, key)
        acquired = await self._redis.set(  # type: ignore[misc]
            lock_key, b"1", ex=self._lock_seconds, nx=True
        )
        if acquired:
            cached = await self.fetch(scope, user_id, key)
            return LockResult(acquired=True, cached=cached)
        cached = await self.fetch(scope, user_id, key)
        return LockResult(acquired=False, cached=cached)

    # reads a cached response if one exists
    async def fetch(
        self, scope: str, user_id: str | None, key: str
    ) -> StoredResponse | None:
        raw = await self._redis.get(_result_key(scope, user_id, key))  # type: ignore[misc]
        if raw is None:
            return None
        return _deserialise(raw)

    # caches a response and releases the in flight lock
    async def save(
        self,
        scope: str,
        user_id: str | None,
        key: str,
        response: StoredResponse,
        *,
        ttl_seconds: int,
    ) -> None:
        await self._redis.set(  # type: ignore[misc]
            _result_key(scope, user_id, key),
            _serialise(response),
            ex=ttl_seconds,
        )
        await self._release(scope, user_id, key)

    # releases the in flight lock
    async def release(self, scope: str, user_id: str | None, key: str) -> None:
        await self._release(scope, user_id, key)

    # deletes the in flight lock without letting a failure interrupt the caller
    async def _release(self, scope: str, user_id: str | None, key: str) -> None:
        try:
            await self._redis.delete(_lock_key(scope, user_id, key))  # type: ignore[misc]
        except aioredis.RedisError as exc:
            await logger.awarning("idempotency_lock_release_failed", error=repr(exc))


# strips the headers that must never be replayed from a cached response
def sanitise_response_headers(
    raw: dict[str, str],
    extra_blacklist: frozenset[str] | None = None,
) -> dict[str, str]:
    blacklist = DEFAULT_HEADER_BLACKLIST | (extra_blacklist or frozenset())
    return {k: v for k, v in raw.items() if k.lower() not in blacklist}


# converts a stored response into a json serializable payload
def encode_for_replay(response: StoredResponse) -> dict[str, Any]:
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.body,
        "fingerprint": response.fingerprint,
    }
