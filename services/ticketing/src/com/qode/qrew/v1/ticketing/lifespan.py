from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.ticketing.core.idempotency import close_idempotency_store
from com.qode.qrew.v1.ticketing.core.locking import close_locking
from com.qode.qrew.v1.ticketing.core.observability import shutdown_tracing
from com.qode.qrew.v1.ticketing.settings import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("ticketing.startup")
    if settings.nats_url:
        try:
            from common.broker.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("ticketing.nats_connected")
        except Exception as exc:
            await logger.awarning("ticketing.nats_unavailable", error=repr(exc))
    yield
    await close_idempotency_store()
    await close_locking()
    try:
        from common.broker.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception:
        pass
    shutdown_tracing()
    await logger.ainfo("ticketing.shutdown")
