# entry point that starts the entry background worker
import asyncio

import structlog
from messaging.client import init_nats
from observability import setup_worker_observability, shutdown_tracing
from worker import run_nats_subscribers

from com.qode.qrew.v1.entry.core.config import settings
from com.qode.qrew.v1.entry.worker.subscribers.catalog import run_catalog_projector
from com.qode.qrew.v1.entry.worker.subscribers.ticketing import run_projector

logger = structlog.get_logger(__name__)


# connects to nats and starts the projectors the entry service keeps
async def main() -> None:
    setup_worker_observability(
        service_name=f"{settings.app_name}-worker",
        version=settings.version,
        debug=settings.debug,
        otel_enabled=settings.otel_enabled,
        otel_endpoint=settings.otel_endpoint,
    )
    if not settings.nats_url:
        await logger.awarning("entry_worker.no_nats_url")
        return

    await init_nats(settings.nats_url)
    await run_nats_subscribers("entry", run_projector(), run_catalog_projector())
    shutdown_tracing()


# runs the worker main coroutine until it stops
def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
