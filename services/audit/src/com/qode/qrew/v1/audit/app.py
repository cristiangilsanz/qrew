import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.audit.core.lifespan import lifespan
from com.qode.qrew.v1.audit.routers import router
from com.qode.qrew.v1.audit.routers.errors import default_responses, register_exception_handlers
from com.qode.qrew.v1.audit.core.config import settings
from observability import setup_tracing

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

app.include_router(router)


@app.get("/health", tags=["probes"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
