"""Subscribes to the fanout subject and delivers incoming messages to local WebSocket connections."""

import asyncio
import json
from typing import Any

import structlog

from com.qode.qrew.v1.gateway.services.hub.hub import get_hub

logger = structlog.get_logger(__name__)

STREAM = "GATEWAY"
SUBJECT = "ws.fanout.v1"
DURABLE = "gateway-fanout-handler"


async def _handle(raw: bytes) -> None:
    try:
        envelope = json.loads(raw.decode())
    except Exception:
        await logger.awarning("gateway_fanout.parse_error")
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


async def run_fanout_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject(SUBJECT)
    except Exception:
        await js.add_stream(name=STREAM, subjects=["ws.>"])  # type: ignore[misc]

    config = ConsumerConfig(
        durable_name=DURABLE,
        deliver_policy=DeliverPolicy.ALL,
        filter_subject=SUBJECT,
    )
    psub = await js.subscribe(
        SUBJECT, durable=DURABLE, config=config, stream=STREAM
    )  # type: ignore[misc]
    await logger.ainfo("gateway_fanout.subscribed", subject=SUBJECT)

    async def _consume() -> None:
        async for msg in psub.messages:  # type: ignore[attr-defined]
            try:
                await _handle(msg.data)  # type: ignore[attr-defined]
                await msg.ack()  # type: ignore[attr-defined]
            except Exception:
                await logger.awarning("gateway_fanout.handler_error")
                await msg.nak()  # type: ignore[attr-defined]

    asyncio.create_task(_consume())

    await logger.ainfo("gateway_fanout.ready")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
