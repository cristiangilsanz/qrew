import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.notification import NotificationStatus
from com.qode.qrew.v1.service.repositories.notification import NotificationRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.notification.channels import (
    deliver as deliver_channel,
)
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


@job(name="notification.deliver")
async def deliver(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Deliver one persisted notification, marking the row and retrying on failure."""
    notification_id = uuid.UUID(payload["notification_id"])
    attempt = int(ctx.get("job_try", 1))
    async with AsyncSessionLocal() as session, session.begin():
        repo = NotificationRepository(session)
        row = await repo.get(notification_id)
        if row is None:
            await logger.awarning(
                "notification_row_missing", notification_id=str(notification_id)
            )
            return
        if row.status == NotificationStatus.sent:
            return
        destination = row.destination
        template_key = row.template_key
        channel = row.channel
        payload_data = dict(row.payload)

    try:
        await deliver_channel(
            channel,
            destination=destination,
            template_key=template_key,
            payload=payload_data,
        )
    except Exception as exc:
        async with AsyncSessionLocal() as session, session.begin():
            row = await NotificationRepository(session).get(notification_id)
            if row is not None:
                row.attempt_count += 1
                row.error = repr(exc)
                if attempt >= settings.notification_max_attempts:
                    row.status = NotificationStatus.failed
        if attempt >= settings.notification_max_attempts:
            try:
                await AuditService().record(
                    action=AuditAction.NOTIFICATION_FAILED,
                    entity_type="notification",
                    entity_id=str(notification_id),
                    payload={"channel": str(channel), "template": template_key},
                )
            except Exception:
                await logger.awarning("notification_failure_audit_write_failed")
        raise

    async with AsyncSessionLocal() as session, session.begin():
        row = await NotificationRepository(session).get(notification_id)
        if row is not None:
            row.status = NotificationStatus.sent
            row.sent_at = datetime.now(UTC)
            row.error = None
