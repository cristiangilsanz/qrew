"""Ticketing NATS worker: subscribes to sales.reservation.* to drive ticket state transitions."""

import asyncio
import json
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.ticketing.core.audit import AuditService
from com.qode.qrew.v1.ticketing.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.ticketing.core.locking import redlock
from com.qode.qrew.v1.ticketing.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.ticketing.repositories.ticket import TicketRepository
from com.qode.qrew.v1.ticketing.services.ticket.transition import transition_ticket

logger = structlog.get_logger(__name__)

STREAM = "SALES"
DURABLE = "ticketing-sales-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception:
        await logger.awarning("sales_events.parse_error")
        return None


async def handle_reservation_created(raw: bytes) -> None:
    """Create ticket rows in `reserved` state when sales creates a reservation."""
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
        event_id = uuid.UUID(str(data["data"]["event_id"]))
        ticket_type_id = uuid.UUID(str(data["data"]["ticket_type_id"]))
        quantity = int(data["data"]["quantity"])
    except (KeyError, ValueError):
        await logger.awarning("sales_events.reservation_created.bad_payload")
        return

    async with AsyncSessionLocal() as session:
        async with redlock(f"reservation:{reservation_id}:tickets", ttl_seconds=10):
            existing = await TicketRepository(session).list_by_reservation(reservation_id)
            if existing:
                await logger.ainfo(
                    "sales_events.reservation_created.already_exists",
                    reservation_id=str(reservation_id),
                )
                return
            for _ in range(quantity):
                session.add(
                    Ticket(
                        reservation_id=reservation_id,
                        event_id=event_id,
                        ticket_type_id=ticket_type_id,
                        owner_user_id=user_id,
                        state=TicketState.reserved,
                    )
                )
            await session.commit()
    await logger.ainfo(
        "sales_events.tickets_created",
        reservation_id=str(reservation_id),
        quantity=quantity,
    )


async def handle_reservation_paid(raw: bytes) -> None:
    """Issue tickets when the reservation transitions to paid."""
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
    except (KeyError, ValueError):
        await logger.awarning("sales_events.reservation_paid.bad_payload")
        return

    async with AsyncSessionLocal() as session:
        async with redlock(f"reservation:{reservation_id}:tickets", ttl_seconds=10):
            audit = AuditService()
            tickets = await TicketRepository(session).list_by_reservation(reservation_id)
            for ticket in tickets:
                if ticket.state == TicketState.reserved:
                    await transition_ticket(
                        session,
                        ticket_id=ticket.id,
                        to_state=TicketState.issued,
                        reason="reservation_paid",
                        actor_id=user_id,
                        audit=audit,
                    )
            await session.commit()
    await logger.ainfo(
        "sales_events.tickets_issued", reservation_id=str(reservation_id)
    )


async def handle_reservation_cancelled(raw: bytes) -> None:
    """Cancel tickets when the reservation is cancelled."""
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
    except (KeyError, ValueError):
        await logger.awarning("sales_events.reservation_cancelled.bad_payload")
        return
    await _cancel_tickets_for_reservation(
        reservation_id, user_id, reason="reservation_cancelled"
    )


async def _cancel_tickets_for_reservation(
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    reason: str,
) -> None:
    cancellable = {TicketState.reserved, TicketState.issued}
    async with AsyncSessionLocal() as session:
        async with redlock(f"reservation:{reservation_id}:tickets", ttl_seconds=10):
            audit = AuditService()
            tickets = await TicketRepository(session).list_by_reservation(reservation_id)
            for ticket in tickets:
                if ticket.state in cancellable:
                    await transition_ticket(
                        session,
                        ticket_id=ticket.id,
                        to_state=TicketState.cancelled,
                        reason=reason,
                        actor_id=user_id,
                        audit=audit,
                    )
            await session.commit()
    await logger.ainfo(
        "sales_events.tickets_cancelled",
        reason=reason,
        reservation_id=str(reservation_id),
    )


_HANDLERS = {
    "sales.reservation.created.v1": handle_reservation_created,
    "sales.reservation.paid.v1": handle_reservation_paid,
    "sales.reservation.cancelled.v1": handle_reservation_cancelled,
}


async def run_payment_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject("sales.>")
    except Exception:
        await js.add_stream(name=STREAM, subjects=["sales.>"])  # type: ignore[misc]

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
        await logger.ainfo("sales_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            async for msg in psub.messages:  # type: ignore[attr-defined]
                try:
                    await h(msg.data)  # type: ignore[attr-defined]
                    await msg.ack()  # type: ignore[attr-defined]
                except Exception:
                    await logger.awarning("sales_events.handler_error")
                    await msg.nak()  # type: ignore[attr-defined]

        asyncio.create_task(_consume())

    await logger.ainfo("sales_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
