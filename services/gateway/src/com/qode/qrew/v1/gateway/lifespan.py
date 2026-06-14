import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from com.qode.qrew.v1.gateway.services.hub.hub import start_hub, stop_hub
from com.qode.qrew.v1.gateway.settings import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("gateway.startup")
    await start_hub()
    nats_task: asyncio.Task[None] | None = None
    if settings.nats_url:
        try:
            from com.qode.qrew.v1.gateway.worker.fanout import run_fanout_subscriber

            nats_task = asyncio.create_task(run_fanout_subscriber(settings.nats_url))
            await logger.ainfo("gateway.nats_connected")
        except Exception as exc:
            await logger.awarning("gateway.nats_unavailable", error=repr(exc))
    yield
    if nats_task is not None:
        nats_task.cancel()
    await stop_hub()
    await logger.ainfo("gateway.shutdown")
