from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from infra.locking import close_locking
from observability import shutdown_tracing
from com.qode.qrew.v1.payments.services.webhook_idempotency import close_webhook_idempotency
from com.qode.qrew.v1.payments.settings import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("payments.startup")
    if settings.nats_url:
        try:
            from common.broker.client import init_nats
            await init_nats(settings.nats_url)
            await logger.ainfo("payments.nats_connected")
        except Exception as exc:
            await logger.awarning("payments.nats_unavailable", error=repr(exc))
    yield
    await close_webhook_idempotency()
    await close_locking()
    try:
        from common.broker.client import close_nats
        await close_nats()
    except Exception:
        pass
    shutdown_tracing()
    await logger.ainfo("payments.shutdown")
