from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("startup")
    await AuditService().ensure_genesis()
    yield
    await logger.ainfo("shutdown")
