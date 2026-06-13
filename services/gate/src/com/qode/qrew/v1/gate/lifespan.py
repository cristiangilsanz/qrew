from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.gate.core.locking import close_locking
from com.qode.qrew.v1.gate.core.observability import shutdown_tracing
from com.qode.qrew.v1.gate.core.ws.publish import close_ws_publisher

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("gate.startup")
    yield
    await close_ws_publisher()
    await close_locking()
    shutdown_tracing()
    await logger.ainfo("gate.shutdown")
