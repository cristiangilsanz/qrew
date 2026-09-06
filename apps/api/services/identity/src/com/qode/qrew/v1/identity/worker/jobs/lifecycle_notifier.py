# reserves the job names other services will use to notify users of lifecycle events
from typing import Any

import structlog

from jobs import job

logger = structlog.get_logger(__name__)


# reports a payment succeeded notification as not yet implemented
@job("notifications.payment_succeeded", max_attempts=3)
async def payment_succeeded(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    await logger.ainfo("notification_disabled", template_key="payment_succeeded")


# reports a payment failed notification as not yet implemented
@job("notifications.payment_failed", max_attempts=3)
async def payment_failed(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    await logger.ainfo("notification_disabled", template_key="payment_failed")


# reports an event cancelled notification as pending
@job("notifications.event_cancelled", max_attempts=3)
async def event_cancelled(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    event_id = payload.get("event_id", "")
    await logger.ainfo("event_cancelled_notification_pending", event_id=event_id)


# reports a chargeback cancellation notification as not yet implemented
@job("notifications.ticket_cancelled_chargeback", max_attempts=3)
async def ticket_cancelled_chargeback(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    await logger.ainfo("notification_disabled", template_key="ticket_cancelled_chargeback")


# reports a refund cancellation notification as not yet implemented
@job("notifications.ticket_cancelled_refund", max_attempts=3)
async def ticket_cancelled_refund(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    await logger.ainfo("notification_disabled", template_key="ticket_cancelled_refund")


# reports a device revoke freeze notification as not yet implemented
@job("notifications.tickets_frozen_device_revoke", max_attempts=3)
async def tickets_frozen_device_revoke(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    await logger.ainfo("notification_disabled", template_key="tickets_frozen_device_revoke")


# reports a ticket restored notification as not yet implemented
@job("notifications.ticket_restored", max_attempts=3)
async def ticket_restored(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    await logger.ainfo("notification_disabled", template_key="ticket_restored")
