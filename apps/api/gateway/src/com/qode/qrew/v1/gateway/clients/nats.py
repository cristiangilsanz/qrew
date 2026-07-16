import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from com.qode.qrew.v1.gateway.hub.hub import get_hub

logger = structlog.get_logger(__name__)

STREAM = "GATEWAY"
SUBJECT = "ws.fanout.v1"
DURABLE = "gateway-fanout-handler"


async def _handle(raw: bytes) -> None:
    try:
        envelope = json.loads(raw.decode())
    except Exception as exc:
        await logger.awarning("gateway_fanout.parse_error", error=repr(exc))
        return

    data: Any = envelope.get("data", {})
    if not isinstance(data, dict):
        return

    channel_key: Any = data.get("channel") or envelope.get("aggregate_id")  # type: ignore[reportUnknownVariableType]
    payload: Any = data.get("payload", data)  # type: ignore[reportUnknownVariableType]

    if not isinstance(channel_key, str) or not isinstance(payload, dict):
        await logger.awarning("gateway_fanout.bad_envelope", channel=channel_key)
        return

    hub = get_hub()
    await hub.deliver(channel_key, payload)  # type: ignore[reportUnknownArgumentType]


async def start_fanout_subscriber(
    nats_url: str,
) -> tuple[asyncio.Task[None], Callable[[], Awaitable[None]]]:

    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    async def _error_cb(exc: Exception) -> None:
        await logger.awarning("gateway_fanout.nats_error", error=repr(exc))

    async def _reconnected_cb() -> None:
        await logger.ainfo("gateway_fanout.nats_reconnected")

    async def _disconnected_cb() -> None:
        await logger.awarning("gateway_fanout.nats_disconnected")

    nc = await nats.connect(  # type: ignore[reportUnknownMemberType]
        nats_url,
        error_cb=_error_cb,
        reconnected_cb=_reconnected_cb,
        disconnected_cb=_disconnected_cb,
    )
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject(SUBJECT)
    except Exception:
        await js.add_stream(name=STREAM, subjects=["ws.>"])  # type: ignore[misc]

    config = ConsumerConfig(
        durable_name=DURABLE,
        deliver_policy=DeliverPolicy.NEW,
        filter_subject=SUBJECT,
    )
    psub = await js.subscribe(SUBJECT, durable=DURABLE, config=config, stream=STREAM)  # type: ignore[misc]
    await logger.ainfo("gateway_fanout.subscribed", subject=SUBJECT)

    async def _consume() -> None:
        async for msg in psub.messages:  # type: ignore[attr-defined]
            await _handle(msg.data)  # type: ignore[attr-defined]
            await msg.ack()  # type: ignore[attr-defined]

    task: asyncio.Task[None] = asyncio.create_task(_consume())

    async def stop() -> None:
        with contextlib.suppress(Exception):
            await psub.unsubscribe()  # type: ignore[attr-defined]
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        try:
            await nc.drain()  # type: ignore[reportUnknownMemberType]
        except Exception as exc:
            await logger.awarning("gateway_fanout.drain_failed", error=repr(exc))

    await logger.ainfo("gateway_fanout.ready")
    return task, stop
