"""Entry point for the ticketing background worker that consumes events from external services."""

import asyncio

import structlog

from com.qode.qrew.v1.ticketing.settings import settings

logger = structlog.get_logger(__name__)


async def main() -> None:
    await logger.ainfo("ticketing_worker.startup")
    nats_url = settings.nats_url
    if not nats_url:
        await logger.awarning("ticketing_worker.no_nats_url")
        return

    from com.qode.qrew.v1.ticketing.worker.catalog_events import run_catalog_event_subscriber
    from com.qode.qrew.v1.ticketing.worker.identity_events import run_identity_event_subscriber
    from com.qode.qrew.v1.ticketing.worker.payment_events import run_payment_event_subscriber

    await asyncio.gather(
        run_payment_event_subscriber(nats_url),
        run_catalog_event_subscriber(nats_url),
        run_identity_event_subscriber(nats_url),
    )


if __name__ == "__main__":
    asyncio.run(main())
