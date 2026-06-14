"""Subscribes to ticket state events and keeps the local projection up to date."""
import asyncio

import nats
import structlog

from com.qode.qrew.v1.gate.settings import settings
from com.qode.qrew.v1.gate.worker.ticket_projector import run_projector

logger = structlog.get_logger(__name__)


async def _run() -> None:
    nc = await nats.connect(settings.nats_url)  # type: ignore[misc]
    await logger.ainfo("worker.connected", nats_url=settings.nats_url)
    await run_projector(nc)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
        await logger.ainfo("worker.shutdown")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
