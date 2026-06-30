import asyncio
import uuid
from decimal import Decimal
from typing import Any

import structlog

from com.qode.qrew.v1.ticketing.core.database import AsyncSessionLocal
from com.qode.qrew.v1.ticketing.repositories.projections import EventVenueContextRepository
from com.qode.qrew.v1.ticketing.worker._parser import parse

logger = structlog.get_logger(__name__)

STREAM = "CATALOG"
DURABLE = "ticketing-catalog-handler"


async def handle_event_published(raw: bytes) -> None:
    data = await parse(raw)
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
    data = await parse(raw)
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
    data = await parse(raw)
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
    data = await parse(raw)
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

    _tasks: list[asyncio.Task[None]] = []
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
            try:
                async for msg in psub.messages:  # type: ignore[attr-defined]
                    try:
                        await h(msg.data)  # type: ignore[attr-defined]
                        await msg.ack()  # type: ignore[attr-defined]
                    except Exception as exc:
                        await logger.awarning("catalog_events.handler_error", error=repr(exc))
                        await msg.nak()  # type: ignore[attr-defined]
            except asyncio.CancelledError:
                raise

        _tasks.append(asyncio.create_task(_consume()))

    await logger.ainfo("catalog_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        for t in _tasks:
            t.cancel()
        await asyncio.gather(*_tasks, return_exceptions=True)
        try:
            await nc.drain()
        except Exception as exc:
            await logger.awarning("catalog_events.drain_failed", error=repr(exc))
