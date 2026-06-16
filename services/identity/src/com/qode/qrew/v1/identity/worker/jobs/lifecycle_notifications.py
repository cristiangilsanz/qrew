import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.identity.core.database import AsyncSessionLocal
from jobs import job
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.services.notification.service import NotificationService

logger = structlog.get_logger(__name__)


async def _get_user(user_id_str: str) -> Any:
    """Looks up a user record by identifier string and returns None if not found."""
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    async with AsyncSessionLocal() as session:
        return await UserRepository(session).get_by_id(user_id)


async def _send(template_key: str, user: Any, payload: dict[str, Any]) -> None:
    if user is None:
        await logger.awarning("notification_user_missing", template_key=template_key)
        return
    await NotificationService().send(
        template_key=template_key,
        payload={"full_name": user.full_name, **payload},
        user=user,
    )


@job("notifications.payment_succeeded", max_attempts=3)
async def payment_succeeded(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Notify the buyer that their payment succeeded."""
    del ctx
    user = await _get_user(payload.get("user_id", ""))
    await _send(
        "payment_succeeded",
        user,
        {"event_name": payload.get("event_name", "")},
    )


@job("notifications.payment_failed", max_attempts=3)
async def payment_failed(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Notify the buyer that their payment failed."""
    del ctx
    user = await _get_user(payload.get("user_id", ""))
    await _send(
        "payment_failed",
        user,
        {
            "event_name": payload.get("event_name", ""),
            "failure_code": payload.get("failure_code"),
        },
    )


@job("notifications.event_cancelled", max_attempts=3)
async def event_cancelled(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Phase 3 stub — fan-out to reservation holders is handled in a future phase."""
    del ctx
    event_id = payload.get("event_id", "")
    await logger.ainfo("event_cancelled_notification_pending", event_id=event_id)


@job("notifications.ticket_cancelled_chargeback", max_attempts=3)
async def ticket_cancelled_chargeback(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    user = await _get_user(payload.get("user_id", ""))
    await _send(
        "ticket_cancelled_chargeback",
        user,
        {"event_name": payload.get("event_name", "")},
    )


@job("notifications.ticket_cancelled_refund", max_attempts=3)
async def ticket_cancelled_refund(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    user = await _get_user(payload.get("user_id", ""))
    await _send(
        "ticket_cancelled_refund",
        user,
        {"event_name": payload.get("event_name", "")},
    )


@job("notifications.tickets_frozen_device_revoke", max_attempts=3)
async def tickets_frozen_device_revoke(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    user = await _get_user(payload.get("user_id", ""))
    await _send(
        "tickets_frozen_device_revoke",
        user,
        {"ticket_count": int(payload.get("ticket_count", 0))},
    )


@job("notifications.ticket_restored", max_attempts=3)
async def ticket_restored(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    user = await _get_user(payload.get("user_id", ""))
    await _send("ticket_restored", user, {"ticket_id": payload.get("ticket_id")})
