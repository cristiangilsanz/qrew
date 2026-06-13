import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.models.event import Event
from com.qode.qrew.v1.service.models.reservation import Reservation
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.services.notification.service import NotificationService

logger = structlog.get_logger(__name__)


async def _payload_for_reservation(
    reservation_id: uuid.UUID,
) -> tuple[Any, str]:
    """Return (user, event_name) for a reservation id, or (None, '') if missing."""
    async with AsyncSessionLocal() as session:
        reservation = await session.get(Reservation, reservation_id)
        if reservation is None:
            return None, ""
        event = await session.get(Event, reservation.event_id)
        user = await UserRepository(session).get_by_id(reservation.user_id)
        return user, event.name if event else ""


async def _send(template_key: str, user: Any, payload: dict[str, Any]) -> None:
    if user is None:
        await logger.awarning("notification_user_missing", template_key=template_key)
        return
    await NotificationService().send(
        template_key=template_key,
        payload={"full_name": user.full_name, **payload},
        user=user,
    )


@job(name="notifications.payment_succeeded", max_attempts=3)
async def payment_succeeded(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Notify the buyer that their payment succeeded."""
    del ctx
    reservation_id = uuid.UUID(payload["reservation_id"])
    user, event_name = await _payload_for_reservation(reservation_id)
    await _send("payment_succeeded", user, {"event_name": event_name})


@job(name="notifications.payment_failed", max_attempts=3)
async def payment_failed(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Notify the buyer that their payment failed."""
    del ctx
    reservation_id = uuid.UUID(payload["reservation_id"])
    user, event_name = await _payload_for_reservation(reservation_id)
    failure_code = payload.get("failure_code")
    await _send(
        "payment_failed",
        user,
        {"event_name": event_name, "failure_code": failure_code},
    )


@job(name="notifications.event_cancelled", max_attempts=3)
async def event_cancelled(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Phase 3 stub fan-out — Phase 4+ will iterate reservation holders."""
    del ctx
    event_id = uuid.UUID(payload["event_id"])
    async with AsyncSessionLocal() as session:
        event = await session.get(Event, event_id)
    if event is None:
        await logger.awarning("event_cancelled_event_missing", event_id=str(event_id))
        return
    await logger.ainfo(
        "event_cancelled_notification_pending",
        event_id=str(event_id),
        event_name=event.name,
    )


@job(name="notifications.ticket_cancelled_chargeback", max_attempts=3)
async def ticket_cancelled_chargeback(
    ctx: dict[str, Any], payload: dict[str, Any]
) -> None:
    del ctx
    reservation_id = uuid.UUID(payload["reservation_id"])
    user, event_name = await _payload_for_reservation(reservation_id)
    await _send("ticket_cancelled_chargeback", user, {"event_name": event_name})


@job(name="notifications.ticket_cancelled_refund", max_attempts=3)
async def ticket_cancelled_refund(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    reservation_id = uuid.UUID(payload["reservation_id"])
    user, event_name = await _payload_for_reservation(reservation_id)
    await _send("ticket_cancelled_refund", user, {"event_name": event_name})


@job(name="notifications.tickets_frozen_device_revoke", max_attempts=3)
async def tickets_frozen_device_revoke(
    ctx: dict[str, Any], payload: dict[str, Any]
) -> None:
    del ctx
    user_id = uuid.UUID(payload["user_id"])
    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(user_id)
    await _send(
        "tickets_frozen_device_revoke",
        user,
        {"ticket_count": int(payload.get("ticket_count", 0))},
    )


@job(name="notifications.ticket_restored", max_attempts=3)
async def ticket_restored(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    user_id = uuid.UUID(payload["user_id"])
    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(user_id)
    await _send("ticket_restored", user, {"ticket_id": payload.get("ticket_id")})


_ = (
    payment_succeeded,
    payment_failed,
    event_cancelled,
    ticket_cancelled_chargeback,
    ticket_cancelled_refund,
    tickets_frozen_device_revoke,
    ticket_restored,
)
