import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from idempotency.middleware import close_idempotency_store
from locking import close_locking
from com.qode.qrew.v1.sales.core.database import engine
from com.qode.qrew.v1.sales.services.queue.redis_queue import close_queue
from observability import setup_tracing, shutdown_tracing
from com.qode.qrew.v1.sales.worker.jobs.queue_admit import admit_next
from com.qode.qrew.v1.sales.worker.jobs.reservation_sweep import sweep_expired
from com.qode.qrew.v1.sales.services.fraud.dependencies import close_fraud
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)


async def _run_periodic(fn: object, interval_seconds: int) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await fn()  # type: ignore[operator]
        except Exception as exc:
            await logger.awarning("periodic_job_failed", fn=str(fn), error=repr(exc))


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
    await logger.ainfo("sales.startup")
    if settings.nats_url:
        try:
            from broker.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("sales.nats_connected")
        except Exception as exc:
            await logger.awarning("sales.nats_unavailable", error=repr(exc))

    sweep_task = asyncio.create_task(_run_periodic(sweep_expired, 60))
    admit_task = asyncio.create_task(_run_periodic(admit_next, 60))

    yield

    sweep_task.cancel()
    admit_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.gather(sweep_task, admit_task, return_exceptions=True)
    await engine.dispose()
    await close_queue()
    await close_fraud()
    await close_idempotency_store()
    await close_locking()
    try:
        from broker.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception as exc:
        await logger.awarning("sales.nats_close_failed", error=repr(exc))
    shutdown_tracing()
    await logger.ainfo("sales.shutdown")
