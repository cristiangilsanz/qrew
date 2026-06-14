import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.sales.services.idempotency.middleware import close_idempotency_store
from infra.locking import close_locking
from observability import shutdown_tracing
from com.qode.qrew.v1.sales.worker.jobs.queue_admit import admit_next
from com.qode.qrew.v1.sales.worker.jobs.reservation_sweep import sweep_expired
from com.qode.qrew.v1.sales.services.fraud.dependencies import close_fraud
from com.qode.qrew.v1.sales.settings import settings

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
    await logger.ainfo("sales.startup")
    if settings.nats_url:
        try:
            from common.broker.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("sales.nats_connected")
        except Exception as exc:
            await logger.awarning("sales.nats_unavailable", error=repr(exc))

    sweep_task = asyncio.create_task(_run_periodic(sweep_expired, 60))
    admit_task = asyncio.create_task(_run_periodic(admit_next, 60))

    yield

    sweep_task.cancel()
    admit_task.cancel()
    await close_fraud()
    await close_idempotency_store()
    await close_locking()
    try:
        from common.broker.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception:
        pass
    shutdown_tracing()
    await logger.ainfo("sales.shutdown")
