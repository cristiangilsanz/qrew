import uuid
from typing import Any

import structlog

from com.qode.qrew.v1.identity.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.core.jobs import enqueue
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from com.qode.qrew.v1.identity.repositories.notification import NotificationRepository
from com.qode.qrew.v1.identity.services.notification.templates import (
    channel_for_template,
)
from com.qode.qrew.v1.identity.settings import settings

logger = structlog.get_logger(__name__)

_JOB_NAME = "notification.deliver"


def _resolve_destination(
    channel: NotificationChannel,
    user: User | None,
    overrides: dict[NotificationChannel, str] | None,
) -> str:
    if overrides and channel in overrides:
        return overrides[channel]
    if user is None:
        raise ValueError(f"no destination for channel {channel}")
    if channel == NotificationChannel.email:
        return user.email
    return user.phone_number


class NotificationService:
    """Persist notifications and enqueue their delivery."""

    async def send(
        self,
        *,
        template_key: str,
        payload: dict[str, Any],
        channels: list[NotificationChannel] | None = None,
        user: User | None = None,
        destinations: dict[NotificationChannel, str] | None = None,
    ) -> list[uuid.UUID]:
        """Persist one row per channel and schedule its delivery."""
        target_channels = channels or [channel_for_template(template_key)]
        ids: list[uuid.UUID] = []
        async with AsyncSessionLocal() as session, session.begin():
            repo = NotificationRepository(session)
            for channel in target_channels:
                destination = _resolve_destination(channel, user, destinations)
                row = Notification(
                    user_id=user.id if user else None,
                    channel=channel,
                    template_key=template_key,
                    payload=payload,
                    status=NotificationStatus.pending,
                )
                row.destination = destination
                await repo.insert(row)
                ids.append(row.id)

        if not settings.notification_enabled:
            await logger.ainfo("notification_dispatch_skipped", count=len(ids))
            return ids

        for notification_id in ids:
            try:
                await enqueue(_JOB_NAME, {"notification_id": str(notification_id)})
            except Exception as exc:
                await logger.awarning(
                    "notification_enqueue_failed",
                    notification_id=str(notification_id),
                    error=repr(exc),
                )
        return ids
