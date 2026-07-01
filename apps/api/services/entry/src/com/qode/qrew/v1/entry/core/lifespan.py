from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from idempotency.middleware import close_idempotency_store
from locking import close_locking
from observability import setup_tracing, shutdown_tracing

from com.qode.qrew.v1.entry.core.config import settings
from com.qode.qrew.v1.entry.core.database import engine

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
    if settings.nats_url:
        try:
            from messaging.client import init_nats

            await init_nats(settings.nats_url)
            await logger.ainfo("entry.nats_connected")
        except Exception as exc:
            await logger.awarning("entry.nats_unavailable", error=repr(exc))
    await logger.ainfo("entry.startup")
    yield
    await engine.dispose()
    await close_idempotency_store()
    await close_locking()
    try:
        from messaging.client import close_nats

        await close_nats()
    except Exception as exc:
        await logger.awarning("entry.nats_close_failed", error=repr(exc))
    shutdown_tracing()
    await logger.ainfo("entry.shutdown")
