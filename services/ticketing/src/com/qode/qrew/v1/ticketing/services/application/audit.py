import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AuditService:
    """Forwards audit events to the message broker for central processing."""

    async def record(
        self,
        *,
        action: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            from messaging.publisher import publish as nats_publish  # type: ignore[import-not-found]
            from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-not-found]

            envelope = EventEnvelope(
                occurred_at=datetime.now(UTC),
                aggregate_type=entity_type or "system",
                aggregate_id=entity_id or "",
                actor_id=str(actor_id) if actor_id else None,
                data={
                    "action": str(action),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "payload": payload or {},
                },
            )
            await nats_publish("audit.events.v1", envelope)
        except Exception as exc:
            await logger.awarning("audit_publish_failed", action=action, error=repr(exc))
