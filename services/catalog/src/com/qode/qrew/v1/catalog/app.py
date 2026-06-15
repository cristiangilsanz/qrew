import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from com.qode.qrew.v1.catalog.routers.errors import default_responses, register_exception_handlers
from com.qode.qrew.v1.catalog.routers.health import router as probes_router
from idempotency.middleware import IdempotencyMiddleware
from com.qode.qrew.v1.catalog.core.dependencies import limiter
from middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from observability import setup_tracing
from com.qode.qrew.v1.catalog.core.lifespan import lifespan
from com.qode.qrew.v1.catalog.routers import router as v1_router
from com.qode.qrew.v1.catalog.core.config import settings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if settings.debug
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    responses=default_responses,
)

setup_tracing(
    service_name=settings.app_name,
    version=settings.version,
    environment="development" if settings.debug else "production",
    app=app,
)
register_exception_handlers(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    IdempotencyMiddleware,
    redis_url=settings.redis_url,
    lock_seconds=settings.idempotency_lock_seconds,
    enabled=settings.idempotency_enabled,
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(probes_router)
app.include_router(v1_router)
