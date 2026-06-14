import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.audit.lifespan import lifespan
from com.qode.qrew.v1.audit.routers import router
from com.qode.qrew.v1.audit.settings import settings

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

app.include_router(router)


@app.get("/health", tags=["probes"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
