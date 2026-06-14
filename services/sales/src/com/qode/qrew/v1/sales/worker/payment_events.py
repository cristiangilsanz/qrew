"""Sales NATS worker: subscribes to payments.* to drive reservation state transitions."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from com.qode.qrew.v1.sales.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.core.locking import redlock
from com.qode.qrew.v1.sales.models.reservation import Reservation, ReservationStatus
from com.qode.qrew.v1.sales.repositories.projections import TicketTypeInventoryRepository
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository

logger = structlog.get_logger(__name__)

STREAM = "PAYMENTS"
DURABLE = "sales-payment-handler"


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
        async with redlock(f"reservation:{reservation_id}:lifecycle", ttl_seconds=10):
            repo = ReservationRepository(session)
            reservation = await repo.get_by_id(reservation_id)
            if reservation is None:
                await logger.awarning(
                    "payment_events.succeeded.not_found",
                    reservation_id=str(reservation_id),
                )
                return
            if reservation.status != ReservationStatus.reserved:
                await logger.awarning(
                    "payment_events.succeeded.skip",
                    status=reservation.status.value,
                    reservation_id=str(reservation_id),
                )
                return
            reservation.status = ReservationStatus.paid
            await session.flush()
            await session.commit()
    await _publish_reservation_paid(reservation, user_id)
    await logger.ainfo(
        "payment_events.succeeded", reservation_id=str(reservation_id)
    )


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
    await _cancel_reservation(reservation_id, user_id, reason="payment_refunded")


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
    await _cancel_reservation(reservation_id, user_id, reason="chargeback_opened")


async def _cancel_reservation(
    reservation_id: uuid.UUID, user_id: uuid.UUID, *, reason: str
) -> None:
    reservation: Reservation | None = None
    async with AsyncSessionLocal() as session:
        async with redlock(f"reservation:{reservation_id}:lifecycle", ttl_seconds=10):
            repo = ReservationRepository(session)
            reservation = await repo.get_by_id(reservation_id)
            if reservation is None:
                return
            if reservation.status in {
                ReservationStatus.cancelled,
                ReservationStatus.expired,
            }:
                return
            inventory_repo = TicketTypeInventoryRepository(session)
            inventory = await inventory_repo.get_by_id(reservation.ticket_type_id)
            reservation.status = ReservationStatus.cancelled
            if inventory is not None:
                inventory.reserved_count = max(
                    0, inventory.reserved_count - reservation.quantity
                )
            await session.flush()
            await session.commit()
    await _publish_reservation_cancelled(reservation, user_id)
    await logger.ainfo(
        "payment_events.reservation_cancelled",
        reason=reason,
        reservation_id=str(reservation_id),
    )


async def _publish_reservation_paid(
    reservation: Reservation, user_id: uuid.UUID
) -> None:
    try:
        from common.broker.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from common.events.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(reservation.id),
            actor_id=str(user_id),
            data={
                "reservation_id": str(reservation.id),
                "user_id": str(reservation.user_id),
                "event_id": str(reservation.event_id),
                "ticket_type_id": str(reservation.ticket_type_id),
                "quantity": reservation.quantity,
            },
        )
        await nats_publish("sales.reservation.paid.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.paid.v1",
            error=repr(exc),
        )


async def _publish_reservation_cancelled(
    reservation: Reservation, user_id: uuid.UUID
) -> None:
    try:
        from common.broker.publisher import publish as nats_publish  # type: ignore[import-untyped]
        from common.events.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="reservation",
            aggregate_id=str(reservation.id),
            actor_id=str(user_id),
            data={
                "reservation_id": str(reservation.id),
                "user_id": str(reservation.user_id),
                "event_id": str(reservation.event_id),
                "ticket_type_id": str(reservation.ticket_type_id),
                "quantity": reservation.quantity,
            },
        )
        await nats_publish("sales.reservation.cancelled.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed",
            subject="sales.reservation.cancelled.v1",
            error=repr(exc),
        )


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
