import asyncio
import signal
from collections.abc import Coroutine
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def run_nats_subscribers(
    service_name: str,
    *subscribers: Coroutine[Any, Any, None],
) -> None:
    """Run one or more async NATS subscriber coroutines with graceful shutdown."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

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
