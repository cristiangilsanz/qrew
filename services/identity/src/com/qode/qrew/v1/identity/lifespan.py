from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.identity.core.idempotency import close_idempotency_store
from com.qode.qrew.v1.identity.core.jobs.pool import close_pool
from com.qode.qrew.v1.identity.core.locking import close_locking
from com.qode.qrew.v1.identity.core.observability import shutdown_tracing
from com.qode.qrew.v1.identity.core.ratelimit.dependencies import close_ratelimiter
from com.qode.qrew.v1.identity.core.ws import start_hub, stop_hub
from com.qode.qrew.v1.identity.settings import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("identity.startup")
    await start_hub()
    if settings.nats_url:
        try:
            from common.broker.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("identity.nats_connected")
        except Exception as exc:
            await logger.awarning("identity.nats_unavailable", error=repr(exc))
    yield
    await stop_hub()
    await close_pool()
    await close_ratelimiter()
    await close_idempotency_store()
    await close_locking()
    try:
        from common.broker.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception:
        pass
    shutdown_tracing()
    await logger.ainfo("identity.shutdown")
