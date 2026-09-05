# entry point that starts the payments arq worker
import asyncio
from typing import Any

import structlog
from db.redis import redis_settings_from_url
from jobs import build_worker_settings
from messaging.client import close_nats, init_nats

from com.qode.qrew.v1.payments.core.config import settings

import com.qode.qrew.v1.payments.worker.jobs.outbox_drainer  # noqa: F401  # pyright: ignore[reportUnusedImport]

logger = structlog.get_logger(__name__)


WorkerSettings = build_worker_settings(
    redis_settings_from_url(settings.redis_url), queue_name="qrew:jobs:payments"
)


# opens the nats connection the drainer publishes through
async def _on_startup(ctx: dict[str, Any]) -> None:
    del ctx
    if not settings.nats_url:
        await logger.awarning("payments_worker.no_nats_url")
        return
    await init_nats(settings.nats_url)


# closes the nats connection when the worker stops
async def _on_shutdown(ctx: dict[str, Any]) -> None:
    del ctx
    await close_nats()


WorkerSettings.on_startup = _on_startup  # type: ignore[attr-defined]
WorkerSettings.on_shutdown = _on_shutdown  # type: ignore[attr-defined]


# runs the arq worker loop
def main() -> None:
    from arq import run_worker

    asyncio.run(run_worker(WorkerSettings))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
