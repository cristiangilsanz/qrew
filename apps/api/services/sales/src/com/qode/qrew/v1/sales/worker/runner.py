# entry point that starts the sales arq worker
import asyncio
from typing import Any

import structlog
from db.redis import redis_settings_from_url
from jobs import build_worker_settings
from messaging.client import close_nats, init_nats
from com.qode.qrew.v1.sales.core.config import settings

import com.qode.qrew.v1.sales.worker.jobs.market_assigner  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.sales.worker.jobs.outbox_drainer  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.sales.worker.jobs.market_expirer  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.sales.worker.jobs.queue_admitter  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.sales.worker.jobs.reservation_expirer  # noqa: F401  # pyright: ignore[reportUnusedImport]

logger = structlog.get_logger(__name__)

WorkerSettings = build_worker_settings(
    redis_settings_from_url(settings.redis_url), queue_name="qrew:jobs:sales"
)


# opens the nats connection the sweepers publish their events through
async def _on_startup(ctx: dict[str, Any]) -> None:
    del ctx
    if not settings.nats_url:
        await logger.awarning("sales_arq_worker.no_nats_url")
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
