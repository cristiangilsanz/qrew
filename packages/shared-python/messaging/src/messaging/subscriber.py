# subscribes to a nats subject and dispatches each message to a handler
from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

import structlog
from nats.js.api import ConsumerConfig, DeliverPolicy

from .client import get_nats

logger = structlog.get_logger(__name__)

Handler = Callable[[bytes], Coroutine[Any, Any, None]]


# subscribes to a subject and runs the consumer loop until cancelled
async def subscribe(
    stream: str,
    subject: str,
    durable: str,
    handler: Handler,
    *,
    ack_wait: int = 30,
) -> None:
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

    # acknowledges each message once its handler has run
    async def _consume() -> None:
        async for msg in psub.messages:  # type: ignore[attr-defined]
            try:
                await handler(msg.data)  # type: ignore[attr-defined]
                await msg.ack()  # type: ignore[attr-defined]
            except Exception as exc:
                await logger.awarning(
                    "nats.handler_error",
                    subject=msg.subject,  # type: ignore[attr-defined]
                    durable=durable,
                    error=repr(exc),
                )
                await msg.nak()  # type: ignore[attr-defined]

    await _consume()


# pulls and yields a batch of messages from a durable subscription
async def iter_messages(
    stream: str,
    subject: str,
    durable: str,
    batch: int = 10,
) -> AsyncGenerator[Any, None]:
    js = get_nats().js
    sub = await js.pull_subscribe(subject, durable=durable, stream=stream)  # type: ignore[misc]
    try:
        msgs = await sub.fetch(batch, timeout=1)  # type: ignore[misc]
    except Exception:
        return
    for msg in msgs:
        yield msg
