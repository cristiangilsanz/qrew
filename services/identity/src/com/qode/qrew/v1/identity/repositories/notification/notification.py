import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.notification import Notification


class NotificationRepository:
    """Persistence layer for notification rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, notification: Notification) -> Notification:
        """Insert a new notification and flush so the id is available."""
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        """Return a notification by id, or None when absent."""
        result = await self._session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def save(self, notification: Notification) -> Notification:
        """Persist updates made to an already-tracked notification."""
        await self._session.flush()
        await self._session.refresh(notification)
        return notification
