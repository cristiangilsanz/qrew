"""Listens for payment saga events from the message broker and triggers notifications and audit records."""

import asyncio
import json
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.identity.core.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.services.outbox import publish_via_outbox
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.services.audit import AuditService

logger = structlog.get_logger(__name__)

STREAM = "PAYMENTS"
DURABLE = "identity-payment-handler"


async def _parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception as exc:
        await logger.awarning("payment_events.parse_error", error=repr(exc))
        return None


def _actor_id(data: dict[str, Any]) -> uuid.UUID:
    try:
        return uuid.UUID(str(data["data"]["user_id"]))
    except (KeyError, ValueError):
        return uuid.uuid4()


async def handle_payment_succeeded(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        payment_id = str(data["data"].get("payment_id", ""))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.succeeded.bad_payload")
        return

    actor_id = _actor_id(data)
    async with AsyncSessionLocal() as session:
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name="notifications.payment_succeeded",
            payload={"user_id": str(actor_id), "reservation_id": str(reservation_id)},
        )
        await AuditService().record(
            action=AuditAction.PAYMENT_SUCCEEDED,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={"reservation_id": str(reservation_id)},
        )
        await session.commit()
    await logger.ainfo("payment_events.succeeded", reservation_id=str(reservation_id))


async def handle_payment_failed(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        payment_id = str(data["data"].get("payment_id", ""))
        failure_code: str | None = data["data"].get("failure_code")
    except (KeyError, ValueError):
        await logger.awarning("payment_events.failed.bad_payload")
        return

    actor_id = _actor_id(data)
    async with AsyncSessionLocal() as session:
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name="notifications.payment_failed",
            payload={
                "user_id": str(actor_id),
                "reservation_id": str(reservation_id),
                "failure_code": failure_code,
            },
        )
        await AuditService().record(
            action=AuditAction.PAYMENT_FAILED,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={"failure_code": failure_code},
        )
        await session.commit()


async def handle_payment_refunded(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        payment_id = str(data["data"].get("payment_id", ""))
        is_full_refund: bool = bool(data["data"].get("is_full_refund", False))
        amount_refunded: int = int(data["data"].get("amount_refunded_cents", 0))
        amount_total: int = int(data["data"].get("amount_total_cents", 0))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.refunded.bad_payload")
        return

    actor_id = _actor_id(data)
    if not is_full_refund:
        async with AsyncSessionLocal() as session:
            await AuditService().record(
                action=AuditAction.PAYMENT_PARTIAL_REFUND,
                actor_id=actor_id,
                entity_type="payment",
                entity_id=payment_id,
                payload={
                    "amount_refunded": amount_refunded,
                    "amount_total": amount_total,
                },
            )
            await session.commit()
        return

    async with AsyncSessionLocal() as session:
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name="notifications.ticket_cancelled_refund",
            payload={
                "user_id": str(actor_id),
                "reservation_id": str(reservation_id),
                "reason": AuditAction.PAYMENT_REFUNDED.value,
            },
        )
        await AuditService().record(
            action=AuditAction.PAYMENT_REFUNDED,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={"reservation_id": str(reservation_id)},
        )
        await session.commit()


async def handle_chargeback_opened(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
        payment_id = str(data["data"].get("payment_id", ""))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.chargeback_opened.bad_payload")
        return

    actor_id = _actor_id(data)
    async with AsyncSessionLocal() as session:
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name="notifications.ticket_cancelled_chargeback",
            payload={
                "user_id": str(actor_id),
                "reservation_id": str(reservation_id),
                "reason": AuditAction.CHARGEBACK_OPENED.value,
            },
        )
        await AuditService().record(
            action=AuditAction.CHARGEBACK_OPENED,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={"reservation_id": str(reservation_id)},
        )
        await session.commit()


async def handle_chargeback_closed(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        payment_id = str(data["data"].get("payment_id", ""))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.chargeback_closed.bad_payload")
        return

    actor_id = _actor_id(data)
    async with AsyncSessionLocal() as session:
        await AuditService().record(
            action=AuditAction.CHARGEBACK_CLOSED,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={},
        )
        await session.commit()


_HANDLERS = {
    "payments.payment.succeeded.v1": handle_payment_succeeded,
    "payments.payment.failed.v1": handle_payment_failed,
    "payments.payment.refunded.v1": handle_payment_refunded,
    "payments.chargeback.opened.v1": handle_chargeback_opened,
    "payments.chargeback.closed.v1": handle_chargeback_closed,
}


async def run_payment_event_subscriber(nats_url: str) -> None:
    import nats
    from nats.js.api import ConsumerConfig, DeliverPolicy

    _tasks: set[asyncio.Task[None]] = set()
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
            try:
                async for msg in psub.messages:  # type: ignore[attr-defined]
                    try:
                        await h(msg.data)  # type: ignore[attr-defined]
                        await msg.ack()  # type: ignore[attr-defined]
                    except Exception as exc:
                        await logger.awarning("payment_events.handler_error", error=repr(exc))
                        await msg.nak()  # type: ignore[attr-defined]
            except asyncio.CancelledError:
                raise

        t = asyncio.create_task(_consume())
        _tasks.add(t)
        t.add_done_callback(_tasks.discard)

    await logger.ainfo("payment_events.all_subscribed")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        for t in list(_tasks):
            t.cancel()
        await asyncio.gather(*_tasks, return_exceptions=True)
        try:
            await nc.drain()
        except Exception as exc:
            await logger.awarning("payment_events.drain_failed", error=repr(exc))
