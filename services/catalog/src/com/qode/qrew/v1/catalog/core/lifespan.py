from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from idempotency.middleware import close_idempotency_store
from locking import close_locking
from observability import shutdown_tracing
from com.qode.qrew.v1.catalog.core.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("catalog.startup")
    if settings.nats_url:
        try:
            from broker.client import init_nats  # type: ignore[import-not-found]

            await init_nats(settings.nats_url)
            await logger.ainfo("catalog.nats_connected")
        except Exception as exc:
            await logger.awarning("catalog.nats_unavailable", error=repr(exc))
    yield
    await close_idempotency_store()
    await close_locking()
    try:
        from broker.client import close_nats  # type: ignore[import-not-found]

        await close_nats()
    except Exception:
        pass
    shutdown_tracing()
    await logger.ainfo("catalog.shutdown")
