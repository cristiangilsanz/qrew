"""Subscribes to catalog events over a message broker and updates the local event and venue projection."""

import asyncio
import json
import uuid
from decimal import Decimal
from typing import Any

import structlog

from com.qode.qrew.v1.ticketing.database import AsyncSessionLocal
from com.qode.qrew.v1.ticketing.repositories.projections import EventVenueContextRepository

logger = structlog.get_logger(__name__)

STREAM = "CATALOG"
DURABLE = "ticketing-catalog-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception:
        await logger.awarning("catalog_events.parse_error")
        return None


async def handle_event_published(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_published.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await EventVenueContextRepository(session).upsert_event(
            event_id=event_id,
            venue_id=venue_id,
            event_status="published",
        )
        await session.commit()
    await logger.ainfo("catalog_events.event_published", event_id=str(event_id))


async def handle_event_cancelled(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_cancelled.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await EventVenueContextRepository(session).upsert_event(
            event_id=event_id,
            venue_id=venue_id,
            event_status="cancelled",
        )
        await session.commit()
    await logger.ainfo("catalog_events.event_cancelled", event_id=str(event_id))


async def handle_event_draft(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_draft.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await EventVenueContextRepository(session).upsert_event(
            event_id=event_id,
            venue_id=venue_id,
            event_status="draft",
        )
        await session.commit()


async def handle_venue_created(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
        event_id_raw = data["data"].get("event_id")
        if event_id_raw is None:
            return
        event_id = uuid.UUID(str(event_id_raw))
        latitude = Decimal(str(data["data"]["latitude"]))
        longitude = Decimal(str(data["data"]["longitude"]))
        geofence_radius_m = int(data["data"]["geofence_radius_m"])
        timezone = str(data["data"]["timezone"])
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.venue_created.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await EventVenueContextRepository(session).upsert_venue(
            event_id=event_id,
            venue_id=venue_id,
            latitude=latitude,
            longitude=longitude,
            geofence_radius_m=geofence_radius_m,
            timezone=timezone,
        )
        await session.commit()
    await logger.ainfo("catalog_events.venue_created", venue_id=str(venue_id))


_HANDLERS = {
    "catalog.event.published.v1": handle_event_published,
    "catalog.event.cancelled.v1": handle_event_cancelled,
    "catalog.event.draft.v1": handle_event_draft,
    "catalog.venue.created.v1": handle_venue_created,
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
        psub = await js.subscribe(
            subject, durable=durable, config=config, stream=STREAM
        )  # type: ignore[misc]
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
