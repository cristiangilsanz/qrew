from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from idempotency.middleware import close_idempotency_store
from observability import setup_tracing, shutdown_tracing
from com.qode.qrew.v1.gateway.hub.hub import start_hub, stop_hub
from com.qode.qrew.v1.gateway.core.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_tracing(
        service_name=settings.app_name,
        version=settings.version,
        environment="production" if not settings.debug else "development",
        otel_enabled=settings.otel_enabled,
        otel_endpoint=settings.otel_endpoint,
        app=app,
    )

    await logger.ainfo("gateway.startup")

    if not settings.access_jwt_private_key:
        raise RuntimeError("Gateway: access_jwt_private_key is not configured")

    await start_hub()

    nats_stop: Callable[[], Awaitable[None]] | None = None

    if settings.nats_url:
        from com.qode.qrew.v1.gateway.clients.nats import start_fanout_subscriber

        _, nats_stop = await start_fanout_subscriber(settings.nats_url)
        await logger.ainfo("gateway.nats_connected")

    yield

    if nats_stop is not None:
        await nats_stop()

    await close_idempotency_store()
    await stop_hub()
    shutdown_tracing()
    await logger.ainfo("gateway.shutdown")
