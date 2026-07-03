from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from idempotency.middleware import IdempotencyMiddleware
from middleware import RequestIDMiddleware, SecurityHeadersMiddleware

from com.qode.qrew.v1.gateway.core.config import settings

# Starlette wraps middleware in LIFO order


def register_middleware(app: FastAPI) -> None:
    limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        IdempotencyMiddleware,
        redis_url=settings.redis_url,
        lock_seconds=settings.idempotency_lock_seconds,
        enabled=settings.idempotency_enabled,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    )
