from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.service.core.idempotency import close_idempotency_store
from com.qode.qrew.v1.service.core.jobs.pool import close_pool
from com.qode.qrew.v1.service.core.observability import shutdown_tracing
from com.qode.qrew.v1.service.core.ratelimit.dependencies import close_ratelimiter
from com.qode.qrew.v1.service.core.ws import start_hub, stop_hub
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("startup")
    await AuditService().ensure_genesis()
    await start_hub()
    yield
    await stop_hub()
    await close_pool()
    await close_ratelimiter()
    await close_idempotency_store()
    shutdown_tracing()
    await logger.ainfo("shutdown")
