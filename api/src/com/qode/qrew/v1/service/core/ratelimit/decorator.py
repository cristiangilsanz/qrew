from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

import structlog
from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from com.qode.qrew.v1.service.core.ratelimit.errors import RateLimitedError
from com.qode.qrew.v1.service.core.ratelimit.limiter import RateLimiter
from com.qode.qrew.v1.service.core.ratelimit.scopes import (
    ALLOWED_SCOPES,
    build_scope_key,
    resolve_scope_value,
)

logger = structlog.get_logger(__name__)

RateLimitRule = tuple[str, int, int]


def rate_limit(
    rules: list[RateLimitRule],
    *,
    limiter_factory: Callable[[Request], Awaitable[RateLimiter]] | None = None,
    on_rejection: Callable[[Request, RateLimitedError], Awaitable[None]] | None = None,
) -> Callable[..., Any]:
    """Reject a request that breaches any of the given rules."""
    for scope, limit, window in rules:
        if scope not in ALLOWED_SCOPES:
            raise ValueError(f"unknown rate-limit scope: {scope}")
        if limit < 1 or window < 1:
            raise ValueError("limit and window must be positive integers")

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(args, kwargs)
            if request is None or limiter_factory is None:
                return await func(*args, **kwargs)

            checks: list[tuple[str, int, int]] = []
            for scope, limit, window in rules:
                value = await resolve_scope_value(scope, request)
                if value is None:
                    continue
                checks.append((build_scope_key(scope, value), limit, window))

            if not checks:
                return await func(*args, **kwargs)

            limiter = await limiter_factory(request)
            try:
                await limiter.check_many(checks)
            except RateLimitedError as exc:
                if on_rejection is not None:
                    try:
                        await on_rejection(request, exc)
                    except Exception:
                        await logger.awarning("ratelimit_audit_failed")
                raise HTTPException(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Rate limit exceeded",
                        "field": None,
                    },
                    headers={"Retry-After": str(max(exc.retry_after_seconds, 1))},
                ) from exc

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _find_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    candidate = kwargs.get("request")
    if isinstance(candidate, Request):
        return candidate  # type: ignore[return-value]
    for arg in args:
        if isinstance(arg, Request):
            return arg  # type: ignore[return-value]
    return None
