import redis.asyncio as aioredis
from fastapi import Request

from com.qode.qrew.v1.identity.core.ratelimit.audit import make_audit_rejection_handler
from com.qode.qrew.v1.identity.core.ratelimit.errors import RateLimitedError
from com.qode.qrew.v1.identity.core.ratelimit.limiter import RateLimiter
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.settings import settings


class _State:
    limiter: RateLimiter | None = None
    redis: aioredis.Redis | None = None  # type: ignore[type-arg]


async def _ensure_limiter() -> RateLimiter:
    if _State.limiter is None:
        _State.redis = aioredis.from_url(settings.redis_url, decode_responses=False)  # type: ignore[type-arg]
        _State.limiter = RateLimiter(_State.redis)
    return _State.limiter


async def close_ratelimiter() -> None:
    """Release the shared Redis client on shutdown."""
    if _State.redis is not None:
        await _State.redis.aclose()
    _State.redis = None
    _State.limiter = None


async def limiter_for(request: Request) -> RateLimiter:
    """Decorator-friendly factory returning the shared limiter."""
    del request
    return await _ensure_limiter()


async def audit_on_rejection(request: Request, exc: RateLimitedError) -> None:
    """Decorator-friendly rejection handler that records audit events."""
    handler = make_audit_rejection_handler(AuditService())
    await handler(request, exc)
