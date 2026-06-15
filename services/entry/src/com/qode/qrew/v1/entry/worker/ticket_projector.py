"""Subscribes to ticket state change events and keeps the local ticket projection up to date."""
import asyncio
import json
import uuid
from typing import Any

import structlog

from broker.client import get_nats
from com.qode.qrew.v1.entry.core.database import AsyncSessionLocal
from com.qode.qrew.v1.entry.repositories.ticket_context import TicketContextRepository

logger = structlog.get_logger(__name__)

SUBJECT = "ticketing.ticket.state_changed"


async def handle_ticket_state_changed(msg: Any) -> None:
    try:
        data = json.loads(msg.data.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        await logger.awarning("ticket_projector.invalid_message")
        return

    try:
        ticket_id = uuid.UUID(str(data["ticket_id"]))
        event_id = uuid.UUID(str(data["event_id"]))
        state = str(data["state"])
    except (KeyError, ValueError):
        await logger.awarning("ticket_projector.missing_fields", data=data)
        return

    venue_id_raw = data.get("venue_id")
    owner_raw = data.get("owner_user_id")
    device_raw = data.get("bound_device_id")

    venue_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    bound_device_id: uuid.UUID | None = None

    try:
        if venue_id_raw:
            venue_id = uuid.UUID(str(venue_id_raw))
        if owner_raw:
            owner_user_id = uuid.UUID(str(owner_raw))
        if device_raw:
            bound_device_id = uuid.UUID(str(device_raw))
    except ValueError:
        pass

    async with AsyncSessionLocal() as session:
        repo = TicketContextRepository(session)
        await repo.upsert(
            ticket_id,
            event_id,
            state,
            venue_id=venue_id,
            owner_user_id=owner_user_id,
            bound_device_id=bound_device_id,
        )
        await session.commit()

    await logger.ainfo(
        "ticket_projector.upserted",
        ticket_id=str(ticket_id),
        state=state,
    )


async def run_projector() -> None:
    nc = get_nats()
    js = nc.js
    try:
        await js.subscribe(SUBJECT, cb=handle_ticket_state_changed, durable="entry-projector")
        await logger.ainfo("ticket_projector.subscribed", subject=SUBJECT)
    except Exception as exc:
        await logger.awarning("ticket_projector.subscribe_failed", error=repr(exc))
        return

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
