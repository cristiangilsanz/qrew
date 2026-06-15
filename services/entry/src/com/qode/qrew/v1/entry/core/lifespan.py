from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from locking import close_locking
from observability import shutdown_tracing

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("entry.startup")
    yield
    await close_locking()
    shutdown_tracing()
    await logger.ainfo("entry.shutdown")
