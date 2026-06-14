"""Ticketing NATS worker: subscribes to payments.* to drive ticket state transitions."""

import asyncio
import json
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.ticketing.core.audit import AuditService
from com.qode.qrew.v1.ticketing.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.ticketing.core.locking import redlock
from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.repositories.ticket import TicketRepository
from com.qode.qrew.v1.ticketing.services.ticket.transition import transition_ticket

logger = structlog.get_logger(__name__)

STREAM = "PAYMENTS"
DURABLE = "ticketing-payment-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception:
        await logger.awarning("payment_events.parse_error")
        return None


async def handle_payment_succeeded(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.succeeded.bad_payload")
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
                        reason="payment_succeeded",
                        actor_id=user_id,
                        audit=audit,
                    )
            await session.commit()
    await logger.ainfo("payment_events.succeeded", reservation_id=str(reservation_id))


async def handle_payment_refunded(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
        is_full_refund: bool = bool(data["data"].get("is_full_refund", False))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.refunded.bad_payload")
        return

    if not is_full_refund:
        return

    await _cancel_tickets_for_reservation(reservation_id, user_id, reason="payment_refunded")


async def handle_chargeback_opened(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        user_id = uuid.UUID(str(data["data"]["user_id"]))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.chargeback_opened.bad_payload")
        return
    await _cancel_tickets_for_reservation(reservation_id, user_id, reason="chargeback_opened")


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
    await logger.ainfo("payment_events.cancelled_tickets", reason=reason, reservation_id=str(reservation_id))


_HANDLERS = {
    "payments.payment.succeeded.v1": handle_payment_succeeded,
    "payments.payment.refunded.v1": handle_payment_refunded,
    "payments.chargeback.opened.v1": handle_chargeback_opened,
}


async def run_payment_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    nc = await nats.connect(nats_url)  # type: ignore[reportUnknownMemberType]
    js = nc.jetstream()  # type: ignore[reportUnknownMemberType]

    try:
        await js.find_stream_name_by_subject("payments.>")
    except Exception:
        await js.add_stream(name=STREAM, subjects=["payments.>"])  # type: ignore[misc]

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
        await logger.ainfo("payment_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            async for msg in psub.messages:  # type: ignore[attr-defined]
                try:
                    await h(msg.data)  # type: ignore[attr-defined]
                    await msg.ack()  # type: ignore[attr-defined]
                except Exception:
                    await logger.awarning("payment_events.handler_error")
                    await msg.nak()  # type: ignore[attr-defined]

        asyncio.create_task(_consume())

    await logger.ainfo("payment_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await nc.drain()
