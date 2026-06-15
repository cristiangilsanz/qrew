import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from com.qode.qrew.v1.gateway.routing import entry as _entry_channel  # noqa: F401  # type: ignore[reportUnusedImport]
from com.qode.qrew.v1.gateway.routing import me as _me_channel  # noqa: F401  # type: ignore[reportUnusedImport]
from com.qode.qrew.v1.gateway.core.lifespan import lifespan
from com.qode.qrew.v1.gateway.routers.ws import router as ws_router
from com.qode.qrew.v1.gateway.routers.errors import register_exception_handlers
from com.qode.qrew.v1.gateway.core.config import settings

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(ws_router)


@app.get("/health", tags=["probes"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
