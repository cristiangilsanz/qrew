import asyncio

import structlog

from worker import run_nats_subscribers
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


async def main() -> None:
    if not settings.nats_url:
        await logger.awarning("identity_worker.no_nats_url")
        return

    from com.qode.qrew.v1.identity.worker.subscribers.catalog import run_catalog_event_subscriber
    from com.qode.qrew.v1.identity.worker.subscribers.payments import run_payment_event_subscriber

    await run_nats_subscribers(
        "identity",
        run_payment_event_subscriber(settings.nats_url),
        run_catalog_event_subscriber(settings.nats_url),
    )


if __name__ == "__main__":
    asyncio.run(main())
