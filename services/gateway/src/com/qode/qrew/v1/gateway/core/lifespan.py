import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any

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
    )

    await logger.ainfo("gateway.startup")

    if not settings.access_jwt_private_key:
        raise RuntimeError("Gateway: access_jwt_private_key is not configured")

    await start_hub()

    nats_task: asyncio.Task[None] | None = None
    nats_nc: Any = None

    if settings.nats_url:
        from com.qode.qrew.v1.gateway.worker.fanout import start_fanout_subscriber

        nats_task, nats_nc = await start_fanout_subscriber(settings.nats_url)
        await logger.ainfo("gateway.nats_connected")

    yield

    if nats_task is not None:
        nats_task.cancel()
        with suppress(asyncio.CancelledError):
            await nats_task
    if nats_nc is not None:
        try:
            await nats_nc.drain()
        except Exception as exc:
            await logger.awarning("gateway.nats_drain_failed", error=repr(exc))

    await close_idempotency_store()
    await stop_hub()
    shutdown_tracing()
    await logger.ainfo("gateway.shutdown")
