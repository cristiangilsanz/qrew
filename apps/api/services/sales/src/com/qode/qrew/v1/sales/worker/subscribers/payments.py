import asyncio
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.services.application.settlement import SettlementService
from com.qode.qrew.v1.sales.worker._parser import parse

logger = structlog.get_logger(__name__)

STREAM = "PAYMENTS"
DURABLE = "sales-payment-handler"


async def handle_payment_succeeded(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.succeeded.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        reservation = await SettlementService(session).mark_paid(reservation_id)
    if reservation is not None:
        await logger.ainfo("payment_events.succeeded", reservation_id=str(reservation_id))


async def handle_payment_refunded(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        is_full_refund: bool = bool(data["data"].get("is_full_refund", False))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.refunded.bad_payload")
        return
    if not is_full_refund:
        return
    async with AsyncSessionLocal() as session:
        reservation = await SettlementService(session).cancel(
            reservation_id, reason="payment_refunded"
        )
    if reservation is not None:
        await logger.ainfo(
            "payment_events.reservation_cancelled",
            reason="payment_refunded",
            reservation_id=str(reservation_id),
        )


async def handle_chargeback_opened(raw: bytes) -> None:
    data = await parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.chargeback_opened.bad_payload")
        return
    async with AsyncSessionLocal() as session:
        reservation = await SettlementService(session).cancel(
            reservation_id, reason="chargeback_opened"
        )
    if reservation is not None:
        await logger.ainfo(
            "payment_events.reservation_cancelled",
            reason="chargeback_opened",
            reservation_id=str(reservation_id),
        )


_HANDLERS = {
    "payments.payment.succeeded.v1": handle_payment_succeeded,
    "payments.payment.refunded.v1": handle_payment_refunded,
    "payments.chargeback.opened.v1": handle_chargeback_opened,
}


async def run_payment_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    _tasks: list[asyncio.Task[None]] = []
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
        psub = await js.subscribe(subject, durable=durable, config=config, stream=STREAM)  # type: ignore[misc]
        await logger.ainfo("payment_events.subscribed", subject=subject)

        async def _consume(psub: Any = psub, h: Any = handler) -> None:
            async for msg in psub.messages:  # type: ignore[attr-defined]
                try:
                    await h(msg.data)  # type: ignore[attr-defined]
                    await msg.ack()  # type: ignore[attr-defined]
                except Exception as exc:
                    await logger.awarning("payment_events.handler_error", error=repr(exc))
                    await msg.nak()  # type: ignore[attr-defined]

        t = asyncio.create_task(_consume())
        _tasks.append(t)

    await logger.ainfo("payment_events.all_subscribed")
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
            await logger.awarning("payment_events.drain_failed", error=repr(exc))
