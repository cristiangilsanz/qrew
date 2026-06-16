from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from idempotency.middleware import close_idempotency_store
from observability import setup_tracing, shutdown_tracing

from com.qode.qrew.v1.payments.core.config import settings
from com.qode.qrew.v1.payments.core.database import engine
from com.qode.qrew.v1.payments.services.webhook_idempotency import (
    close_webhook_idempotency,
)

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
    await logger.ainfo("payments.startup")
    if settings.nats_url:
        try:
            from broker.client import init_nats

            await init_nats(settings.nats_url)
            await logger.ainfo("payments.nats_connected")
        except Exception as exc:
            await logger.awarning("payments.nats_unavailable", error=repr(exc))
    yield
    await engine.dispose()
    await close_idempotency_store()
    await close_webhook_idempotency()
    if settings.nats_url:
        try:
            from broker.client import close_nats

            await close_nats()
        except Exception as exc:
            await logger.awarning("payments.nats_close_failed", error=repr(exc))
    shutdown_tracing()
    await logger.ainfo("payments.shutdown")
