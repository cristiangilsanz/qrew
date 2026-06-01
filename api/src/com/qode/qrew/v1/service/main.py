import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from com.qode.qrew.v1.service.core.api import (
    default_responses,
    probes_router,
    register_exception_handlers,
)
from com.qode.qrew.v1.service.core.idempotency import IdempotencyMiddleware
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.infra.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from com.qode.qrew.v1.service.core.observability import add_trace_context, setup_tracing
from com.qode.qrew.v1.service.core.ws import router as ws_router
from com.qode.qrew.v1.service.lifespan import lifespan
from com.qode.qrew.v1.service.realtime import me_channel as _me_channel
from com.qode.qrew.v1.service.routers import router as v1_router
from com.qode.qrew.v1.service.settings import settings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_trace_context,
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

_ = _me_channel  # ensure the @channel decorator runs at import time

setup_tracing(app)

register_exception_handlers(app)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(probes_router)
app.include_router(ws_router)
app.include_router(v1_router)
