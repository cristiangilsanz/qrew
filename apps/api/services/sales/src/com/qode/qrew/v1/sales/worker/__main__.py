import asyncio

from messaging.client import init_nats
from worker import run_nats_subscribers
from com.qode.qrew.v1.sales.core.config import settings


async def main() -> None:
    if not settings.nats_url:
        import structlog

        await structlog.get_logger(__name__).awarning("sales_worker.no_nats_url")
        return

    await init_nats(settings.nats_url)

    from com.qode.qrew.v1.sales.worker.subscribers.catalog import run_catalog_event_subscriber
    from com.qode.qrew.v1.sales.worker.subscribers.identity import run_identity_event_subscriber
    from com.qode.qrew.v1.sales.worker.subscribers.payments import run_payment_event_subscriber

    await run_nats_subscribers(
        "sales",
        run_payment_event_subscriber(settings.nats_url),
        run_catalog_event_subscriber(settings.nats_url),
        run_identity_event_subscriber(settings.nats_url),
    )


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
