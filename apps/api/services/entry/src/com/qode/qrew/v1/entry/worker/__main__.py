import asyncio

import structlog
from messaging.client import init_nats
from worker import run_nats_subscribers

from com.qode.qrew.v1.entry.core.config import settings
from com.qode.qrew.v1.entry.worker.subscribers.ticketing import run_projector

logger = structlog.get_logger(__name__)


async def main() -> None:
    if not settings.nats_url:
        await logger.awarning("entry_worker.no_nats_url")
        return

    await init_nats(settings.nats_url)
    await run_nats_subscribers("entry", run_projector())


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
