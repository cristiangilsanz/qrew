import asyncio

from worker import run_nats_subscribers
from com.qode.qrew.v1.ticketing.core.config import settings


async def main() -> None:
    if not settings.nats_url:
        import structlog

        await structlog.get_logger(__name__).awarning("ticketing_worker.no_nats_url")
        return

    from com.qode.qrew.v1.ticketing.worker.subscribers.catalog import run_catalog_event_subscriber
    from com.qode.qrew.v1.ticketing.worker.subscribers.identity import run_identity_event_subscriber
    from com.qode.qrew.v1.ticketing.worker.subscribers.sales import run_sales_event_subscriber

    await run_nats_subscribers(
        "ticketing",
        run_sales_event_subscriber(settings.nats_url),
        run_catalog_event_subscriber(settings.nats_url),
        run_identity_event_subscriber(settings.nats_url),
    )


if __name__ == "__main__":
    asyncio.run(main())
