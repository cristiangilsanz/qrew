import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from jwt import InvalidTokenError

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.core.queue import (
    join_queue,
    queue_position,
    redeem_window_token,
)
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.event import EventStatus
from com.qode.qrew.v1.service.repositories.event import EventRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class QueueError(DomainError):
    """Raised when a queue operation fails a domain rule."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class QueueService:
    """Business logic that orchestrates the Redis-backed queue."""

    def __init__(self, event_repo: EventRepository, audit: AuditService) -> None:
        self._event_repo = event_repo
        self._audit = audit

    @traced("queue.service.join")
    async def join(
        self, *, user_id: uuid.UUID, event_id: uuid.UUID, tiebreak: int
    ) -> int:
        event = await self._event_repo.get_by_id(event_id)
        if event is None or event.status != EventStatus.published:
            raise QueueError("Event not found", field="event_id")
        if not event.queue_required:
            raise QueueError("Event has no queue", field="queue_required")
        now = _now()
        if now > event.sale_ends_at:
            raise QueueError("Sale window is closed", field="sale_window")
        lead = settings.queue_join_lead_seconds
        if (event.sale_starts_at - now).total_seconds() > lead:
            raise QueueError(
                "Queue is not yet open for this event", field="sale_starts_at"
            )
        sale_start_ms = int(event.sale_starts_at.timestamp() * 1000)
        now_ms = int(now.timestamp() * 1000)
        result = await join_queue(
            event_id=event_id,
            user_id=user_id,
            sale_start_ms=sale_start_ms,
            now_ms=now_ms,
            tiebreak=tiebreak,
        )
        if result is None:
            position = await queue_position(event_id, user_id)
            if position is None:
                raise QueueError("Failed to join the queue", field="event_id")
            return position
        await self._record(
            AuditAction.QUEUE_JOINED,
            actor_id=user_id,
            event_id=event_id,
            payload={"position": result.position},
        )
        return result.position

    @traced("queue.service.position")
    async def position(self, *, user_id: uuid.UUID, event_id: uuid.UUID) -> int | None:
        return await queue_position(event_id, user_id)

    @traced("queue.service.redeem")
    async def redeem(self, *, user_id: uuid.UUID, token: str) -> str:
        try:
            reservation_token = await redeem_window_token(token=token, user_id=user_id)
        except InvalidTokenError as exc:
            await self._record(
                AuditAction.QUEUE_REDEEM_FAILED,
                actor_id=user_id,
                event_id=None,
                payload={"reason": str(exc)},
            )
            raise QueueError(
                "Invalid redeem token", field="redeem_window_token"
            ) from exc
        await self._record(
            AuditAction.QUEUE_REDEEMED,
            actor_id=user_id,
            event_id=None,
            payload={},
        )
        return reservation_token

    async def _record(
        self,
        action: AuditAction,
        *,
        actor_id: uuid.UUID,
        event_id: uuid.UUID | None,
        payload: dict[str, Any],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="event" if event_id else "queue",
                entity_id=str(event_id) if event_id else None,
                payload=payload,
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=action)
