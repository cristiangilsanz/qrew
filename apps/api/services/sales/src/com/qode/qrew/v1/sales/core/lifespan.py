import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from idempotency.middleware import close_idempotency_store
from locking import close_locking
from com.qode.qrew.v1.sales.core.database import engine
from com.qode.qrew.v1.sales.services.application.queue.storage import close_queue
from observability import setup_tracing, shutdown_tracing
from com.qode.qrew.v1.sales.worker.jobs.market_assigner import assign_pending
from com.qode.qrew.v1.sales.worker.jobs.market_expirer import sweep_expired as market_sweep_expired
from com.qode.qrew.v1.sales.worker.jobs.queue_admitter import admit_next
from com.qode.qrew.v1.sales.worker.jobs.reservation_expirer import sweep_expired
from com.qode.qrew.v1.sales.services.domain.fraud.dependencies import close_fraud
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)


async def _run_periodic(fn: object, interval_seconds: int) -> None:
    while True:
        try:
            await fn()  # type: ignore[operator]
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
    await logger.ainfo("sales.startup")
    if settings.nats_url:
        try:
            from messaging.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("sales.nats_connected")
        except Exception as exc:
            await logger.awarning("sales.nats_unavailable", error=repr(exc))

    sweep_task = asyncio.create_task(_run_periodic(sweep_expired, 60))
    admit_task = asyncio.create_task(_run_periodic(admit_next, 10))
    market_assign_task = asyncio.create_task(
        _run_periodic(assign_pending, settings.market_assigner_interval_seconds)
    )
    market_expire_task = asyncio.create_task(
        _run_periodic(market_sweep_expired, settings.market_expirer_interval_seconds)
    )

    yield

    sweep_task.cancel()
    admit_task.cancel()
    market_assign_task.cancel()
    market_expire_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.gather(
            sweep_task, admit_task, market_assign_task, market_expire_task,
            return_exceptions=True,
        )
    await engine.dispose()
    await close_queue()
    await close_fraud()
    await close_idempotency_store()
    await close_locking()
    try:
        from messaging.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception as exc:
        await logger.awarning("sales.nats_close_failed", error=repr(exc))
    shutdown_tracing()
    await logger.ainfo("sales.shutdown")
