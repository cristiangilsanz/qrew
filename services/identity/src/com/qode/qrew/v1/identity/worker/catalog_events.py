"""Monolith NATS worker: subscribes to catalog.* lifecycle events."""

import asyncio
import json
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.identity.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.core.outbox import publish_via_outbox

logger = structlog.get_logger(__name__)

STREAM = "CATALOG"
DURABLE = "identity-catalog-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception:
        await logger.awarning("catalog_events.parse_error")
        return None


async def handle_event_cancelled(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_cancelled.bad_payload")
        return

    async with AsyncSessionLocal() as session:
        await publish_via_outbox(
            session,
            aggregate_type="event",
            aggregate_id=str(event_id),
            job_name="notifications.event_cancelled",
            payload={"event_id": str(event_id)},
        )
        await session.commit()
    await logger.ainfo("catalog_events.event_cancelled", event_id=str(event_id))


_HANDLERS = {
    "catalog.event.cancelled.v1": handle_event_cancelled,
}


async def run_catalog_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject("catalog.>")
    except Exception:
        await js.add_stream(name=STREAM, subjects=["catalog.>"])  # type: ignore[misc]

    for subject, handler in _HANDLERS.items():
        durable = f"{DURABLE}-{subject.replace('.', '-')}"
        config = ConsumerConfig(
            durable_name=durable,
            deliver_policy=DeliverPolicy.ALL,
            filter_subject=subject,
        )
        psub = await js.subscribe(subject, durable=durable, config=config, stream=STREAM)  # type: ignore[misc]
        await logger.ainfo("catalog_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            async for msg in psub.messages:  # type: ignore[attr-defined]
                try:
                    await h(msg.data)  # type: ignore[attr-defined]
                    await msg.ack()  # type: ignore[attr-defined]
                except Exception:
                    await logger.awarning("catalog_events.handler_error")
                    await msg.nak()  # type: ignore[attr-defined]

        asyncio.create_task(_consume())

    await logger.ainfo("catalog_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
