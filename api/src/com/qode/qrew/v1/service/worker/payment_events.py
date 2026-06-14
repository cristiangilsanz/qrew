"""Monolith NATS worker: subscribes to payments.* saga events."""

import asyncio
import json
import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.outbox import publish_via_outbox
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)

STREAM = "PAYMENTS"
DURABLE = "monolith-payment-handler"


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
        payment_id = str(data["data"].get("payment_id", ""))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.succeeded.bad_payload")
        return

    async with AsyncSessionLocal() as session:
        repo = ReservationRepository(session)
        reservation = await repo.get_by_id(reservation_id)
        actor_id = reservation.user_id if reservation else uuid.uuid4()
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name="notifications.payment_succeeded",
            payload={"reservation_id": str(reservation_id)},
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

    async with AsyncSessionLocal() as session:
        repo = ReservationRepository(session)
        reservation = await repo.get_by_id(reservation_id)
        actor_id = reservation.user_id if reservation else uuid.uuid4()
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name="notifications.payment_failed",
            payload={
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

    if not is_full_refund:
        async with AsyncSessionLocal() as session:
            reservation = await ReservationRepository(session).get_by_id(reservation_id)
            actor_id = reservation.user_id if reservation else uuid.uuid4()
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

    await _cancel_reservation(
        reservation_id, payment_id, reason=AuditAction.PAYMENT_REFUNDED
    )


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
    await _cancel_reservation(
        reservation_id, payment_id, reason=AuditAction.CHARGEBACK_OPENED
    )


async def handle_chargeback_closed(raw: bytes) -> None:
    data = await _parse(raw)
    if data is None:
        return
    try:
        payment_id = str(data["data"].get("payment_id", ""))
        reservation_id = uuid.UUID(str(data["data"]["reservation_id"]))
    except (KeyError, ValueError):
        await logger.awarning("payment_events.chargeback_closed.bad_payload")
        return

    async with AsyncSessionLocal() as session:
        reservation = await ReservationRepository(session).get_by_id(reservation_id)
        actor_id = reservation.user_id if reservation else uuid.uuid4()
        await AuditService().record(
            action=AuditAction.CHARGEBACK_CLOSED,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={},
        )
        await session.commit()


async def _cancel_reservation(
    reservation_id: uuid.UUID,
    payment_id: str,
    *,
    reason: AuditAction,
) -> None:
    async with AsyncSessionLocal() as session:
        repo = ReservationRepository(session)
        reservation = await repo.get_by_id(reservation_id)
        actor_id = reservation.user_id if reservation else uuid.uuid4()
        job_name = (
            "notifications.ticket_cancelled_chargeback"
            if reason == AuditAction.CHARGEBACK_OPENED
            else "notifications.ticket_cancelled_refund"
        )
        await publish_via_outbox(
            session,
            aggregate_type="payment",
            aggregate_id=payment_id,
            job_name=job_name,
            payload={"reservation_id": str(reservation_id), "reason": reason.value},
        )
        await AuditService().record(
            action=reason,
            actor_id=actor_id,
            entity_type="payment",
            entity_id=payment_id,
            payload={"reservation_id": str(reservation_id)},
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
