"""Monolith NATS worker entry point — subscribes to payment and catalog saga events."""

import asyncio

import structlog

from com.qode.qrew.v1.service.settings import settings
from com.qode.qrew.v1.service.worker.catalog_events import run_catalog_event_subscriber
from com.qode.qrew.v1.service.worker.payment_events import run_payment_event_subscriber

logger = structlog.get_logger(__name__)


async def _run() -> None:
    await logger.ainfo("api_worker.starting", nats_url=settings.nats_url)
    await asyncio.gather(
        run_payment_event_subscriber(settings.nats_url),
        run_catalog_event_subscriber(settings.nats_url),
    )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
