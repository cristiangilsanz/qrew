from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

import structlog
from nats.js.api import ConsumerConfig, DeliverPolicy

from common.broker.client import get_nats

logger = structlog.get_logger(__name__)

Handler = Callable[[bytes], Coroutine[Any, Any, None]]


async def subscribe(
    stream: str,
    subject: str,
    durable: str,
    handler: Handler,
    *,
    ack_wait: int = 30,
) -> None:
    """Register a durable push consumer and process messages with handler.

    Each successfully processed message is acked. Errors are logged and the
    message is nacked so JetStream retries with backoff.
    """
    js = get_nats().js
    config = ConsumerConfig(
        durable_name=durable,
        deliver_policy=DeliverPolicy.ALL,
        ack_wait=ack_wait,
        filter_subject=subject,
    )
    psub = await js.subscribe(subject, durable=durable, config=config, stream=stream)  # type: ignore[misc]
    await logger.ainfo(
        "nats.subscribed", stream=stream, subject=subject, durable=durable
    )

    async def _consume() -> None:
        async for msg in psub.messages:  # type: ignore[attr-defined]
            try:
                await handler(msg.data)  # type: ignore[attr-defined]
                await msg.ack()  # type: ignore[attr-defined]
            except Exception:
                await logger.awarning(
                    "nats.handler_error",
                    subject=msg.subject,  # type: ignore[attr-defined]
                    durable=durable,
                )
                await msg.nak()  # type: ignore[attr-defined]

    await _consume()


async def iter_messages(
    stream: str,
    subject: str,
    durable: str,
    batch: int = 10,
) -> AsyncGenerator[Any, None]:
    """Pull-based consumer for use in Arq jobs — fetches a batch and yields."""
    js = get_nats().js
    sub = await js.pull_subscribe(subject, durable=durable, stream=stream)  # type: ignore[misc]
    try:
        msgs = await sub.fetch(batch, timeout=1)  # type: ignore[misc]
    except Exception:
        return
    for msg in msgs:
        yield msg
