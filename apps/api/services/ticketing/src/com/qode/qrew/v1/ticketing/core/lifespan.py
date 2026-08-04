import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Callable, Coroutine

import structlog
from fastapi import FastAPI

from idempotency.middleware import close_idempotency_store
from locking import close_locking
from observability import setup_tracing, shutdown_tracing
from com.qode.qrew.v1.ticketing.core.config import settings
from com.qode.qrew.v1.ticketing.core.database import engine

logger = structlog.get_logger(__name__)


async def _run_periodic(fn: Callable[[], Coroutine[Any, Any, Any]], interval_seconds: int) -> None:
    while True:
        try:
            await fn()
        except Exception as exc:
            await logger.awarning("periodic_job_failed", fn=str(fn), error=repr(exc))
        await asyncio.sleep(interval_seconds)


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
            from messaging.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("ticketing.nats_connected")
        except Exception as exc:
            await logger.awarning("ticketing.nats_unavailable", error=repr(exc))

    from com.qode.qrew.v1.ticketing.worker.jobs.expired_ticket_purger import purge_expired

    purge_task = asyncio.create_task(_run_periodic(purge_expired, 60))

    yield

    purge_task.cancel()
    try:
        await purge_task
    except asyncio.CancelledError:
        pass

    await engine.dispose()
    await close_idempotency_store()
    await close_locking()
    try:
        from messaging.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception as exc:
        await logger.awarning("ticketing.nats_close_failed", error=repr(exc))
    shutdown_tracing()
    await logger.ainfo("ticketing.shutdown")
