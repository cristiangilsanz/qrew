import logging

import structlog
from fastapi import FastAPI

from exceptions import register_exception_handlers
from observability import add_trace_context

from com.qode.qrew.v1.gateway.channels import entry as _entry_channel  # noqa: F401  # type: ignore[reportUnusedImport]
from com.qode.qrew.v1.gateway.channels import me as _me_channel  # noqa: F401  # type: ignore[reportUnusedImport]
from com.qode.qrew.v1.gateway.core.config import settings
from com.qode.qrew.v1.gateway.core.lifespan import lifespan
from com.qode.qrew.v1.gateway.middleware.register import register_middleware
from com.qode.qrew.v1.gateway.routers.health import router as probes_router
from com.qode.qrew.v1.gateway.routers.ws import router as ws_router

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_trace_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.ExceptionRenderer(),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
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
register_middleware(app)

app.include_router(probes_router)
app.include_router(ws_router)
