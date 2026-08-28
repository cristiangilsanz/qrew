# runs a worker's nats subscribers until a shutdown signal arrives
import asyncio
import signal
from collections.abc import Coroutine
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# runs every subscriber until a shutdown signal or one of them stops
async def run_nats_subscribers(
    service_name: str,
    *subscribers: Coroutine[Any, Any, None],
) -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    # signals the worker to stop
    def _handle_signal() -> None:
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    await logger.ainfo(f"{service_name}.worker_started")

    tasks = [asyncio.create_task(sub) for sub in subscribers]

    try:
        _done, pending = await asyncio.wait(
            [asyncio.create_task(stop_event.wait()), *tasks],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        await logger.ainfo(f"{service_name}.worker_stopped")
