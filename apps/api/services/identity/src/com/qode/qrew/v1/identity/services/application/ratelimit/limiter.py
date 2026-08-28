# shares a redis backed rate limiter across the login and registration endpoints
import redis.asyncio as aioredis
from fastapi import Request

from com.qode.qrew.v1.identity.services.application.ratelimit.reporter import (
    make_audit_rejection_handler,
)
from ratelimit.errors import RateLimitedError
from ratelimit.limiter import RateLimiter
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings


class _State:
    limiter: RateLimiter | None = None
    redis: aioredis.Redis | None = None  # type: ignore[type-arg]


# builds the shared rate limiter the first time it is needed
async def _ensure_limiter() -> RateLimiter:
    if _State.limiter is None:
        _State.redis = aioredis.from_url(settings.redis_url, decode_responses=False)  # type: ignore[type-arg]
        _State.limiter = RateLimiter(_State.redis)
    return _State.limiter


# closes the shared rate limiter's redis client
async def close_ratelimiter() -> None:
    if _State.redis is not None:
        await _State.redis.aclose()
    _State.redis = None
    _State.limiter = None


# returns the shared rate limiter for a request
async def limiter_for(request: Request) -> RateLimiter:
    del request
    return await _ensure_limiter()


# records an audit event when a request is rejected for exceeding its limit
async def audit_on_rejection(request: Request, exc: RateLimitedError) -> None:
    handler = make_audit_rejection_handler(AuditService())
    await handler(request, exc)
