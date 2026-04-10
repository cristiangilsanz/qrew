import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from com.qode.qrew.v1.service.core.exceptions import register_exception_handlers
from com.qode.qrew.v1.service.core.limiter import limiter
from com.qode.qrew.v1.service.core.middleware import RequestIDMiddleware
from com.qode.qrew.v1.service.lifespan import lifespan
from com.qode.qrew.v1.service.routers import router as v1_router
from com.qode.qrew.v1.service.settings import settings

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
)

register_exception_handlers(app)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)

app.include_router(v1_router)
