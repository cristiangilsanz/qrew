from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from idempotency.middleware import close_idempotency_store
from locking import close_locking
from observability import setup_tracing, shutdown_tracing
from com.qode.qrew.v1.ticketing.core.config import settings
from com.qode.qrew.v1.ticketing.core.database import engine

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_tracing(
        service_name=settings.app_name,
        version=settings.version,
        environment="development" if settings.debug else "production",
        otel_enabled=settings.otel_enabled,
        otel_endpoint=settings.otel_endpoint,
        app=app,
    )
    await logger.ainfo("ticketing.startup")
    if settings.nats_url:
        try:
            from broker.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("ticketing.nats_connected")
        except Exception as exc:
            await logger.awarning("ticketing.nats_unavailable", error=repr(exc))
    yield
    await engine.dispose()
    await close_idempotency_store()
    await close_locking()
    try:
        from broker.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception as exc:
        await logger.awarning("ticketing.nats_close_failed", error=repr(exc))
    shutdown_tracing()
    await logger.ainfo("ticketing.shutdown")
