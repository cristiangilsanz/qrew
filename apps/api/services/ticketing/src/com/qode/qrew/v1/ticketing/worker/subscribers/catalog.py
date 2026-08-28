# projects catalog's event lifecycle into the ticketing service's local context
import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog

from com.qode.qrew.v1.ticketing.core.database import AsyncSessionLocal
from com.qode.qrew.v1.ticketing.repositories.projections import EventVenueContextRepository
from com.qode.qrew.v1.ticketing.worker._parser import parse

logger = structlog.get_logger(__name__)

STREAM = "CATALOG"
DURABLE = "ticketing-catalog-handler"


# updates an event's geofence when the message carries venue coordinates
async def _upsert_geofence(
    repo: EventVenueContextRepository,
    data: dict[str, Any],
    *,
    event_id: uuid.UUID,
    venue_id: uuid.UUID,
) -> None:
    payload = data["data"]
    if "latitude" not in payload:
        return
    try:
        await repo.upsert_venue(
            event_id=event_id,
            venue_id=venue_id,
            latitude=Decimal(str(payload["latitude"])),
            longitude=Decimal(str(payload["longitude"])),
            geofence_radius_m=int(payload["geofence_radius_m"]),
            timezone=str(payload["timezone"]),
        )
    except (KeyError, ValueError, ArithmeticError):
        await logger.awarning("catalog_events.geofence.bad_payload", event_id=str(event_id))


# projects a published event and cancels tickets that are no longer valid
async def handle_event_published(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
        starts_at_raw = data["data"].get("starts_at")
        ends_at_raw = data["data"].get("ends_at")
        starts_at = datetime.fromisoformat(starts_at_raw) if starts_at_raw else None
        ends_at = datetime.fromisoformat(ends_at_raw) if ends_at_raw else None
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_published.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        repo = EventVenueContextRepository(session)
        await repo.upsert_event(
            event_id=event_id,
            venue_id=venue_id,
            event_status="published",
            starts_at=starts_at,
            ends_at=ends_at,
        )
        await _upsert_geofence(repo, data, event_id=event_id, venue_id=venue_id)
        await session.commit()
    await logger.ainfo("catalog_events.event_published", event_id=str(event_id))


# cancels every active ticket of a cancelled event
async def handle_event_cancelled(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_cancelled.bad_payload")
        return

    from com.qode.qrew.v1.ticketing.repositories.ticket import TicketRepository
    from com.qode.qrew.v1.ticketing.services.domain.tickets.lifecycle import (
        TicketTransitionError,
        transition_ticket,
    )
    from com.qode.qrew.v1.ticketing.models.ticket import TicketState

    SYSTEM_ACTOR = uuid.UUID("00000000-0000-0000-0000-000000000000")

    async with AsyncSessionLocal() as session:
        tickets = await TicketRepository(session).list_active_by_event(event_id)
        cancelled = 0
        for ticket in tickets:
            try:
                await transition_ticket(
                    session,
                    ticket_id=ticket.id,
                    to_state=TicketState.cancelled,
                    reason="event_cancelled",
                    actor_id=SYSTEM_ACTOR,
                )
                cancelled += 1
            except (TicketTransitionError, Exception) as exc:
                await logger.awarning(
                    "catalog_events.event_cancelled.ticket_cancel_failed",
                    ticket_id=str(ticket.id),
                    error=repr(exc),
                )
        await session.commit()

    await logger.ainfo(
        "catalog_events.event_cancelled",
        event_id=str(event_id),
        tickets_cancelled=cancelled,
    )


# projects a draft event's schedule and venue
async def handle_event_draft(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
        starts_at_raw = data["data"].get("starts_at")
        ends_at_raw = data["data"].get("ends_at")
        starts_at = datetime.fromisoformat(starts_at_raw) if starts_at_raw else None
        ends_at = datetime.fromisoformat(ends_at_raw) if ends_at_raw else None
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_draft.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await EventVenueContextRepository(session).upsert_event(
            event_id=event_id,
            venue_id=venue_id,
            event_status="draft",
            starts_at=starts_at,
            ends_at=ends_at,
        )
        await session.commit()


# projects that an event has become ongoing
async def handle_event_ongoing(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        venue_id = uuid.UUID(str(data["data"]["venue_id"]))
        starts_at_raw = data["data"].get("starts_at")
        ends_at_raw = data["data"].get("ends_at")
        starts_at = datetime.fromisoformat(starts_at_raw) if starts_at_raw else None
        ends_at = datetime.fromisoformat(ends_at_raw) if ends_at_raw else None
    except (KeyError, ValueError):
        await logger.awarning("catalog_events.event_ongoing.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        await EventVenueContextRepository(session).upsert_event(
            event_id=event_id,
            venue_id=venue_id,
            event_status="ongoing",
            starts_at=starts_at,
            ends_at=ends_at,
        )
        await session.commit()
    await logger.ainfo("catalog_events.event_ongoing", event_id=str(event_id))


_HANDLERS = {
    "catalog.event.published.v1": handle_event_published,
    "catalog.event.ongoing.v1": handle_event_ongoing,
    "catalog.event.cancelled.v1": handle_event_cancelled,
    "catalog.event.draft.v1": handle_event_draft,
}


# subscribes to every catalog event subject and dispatches each message
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

        # acknowledges each message once its handler has run
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
