import uuid
from datetime import UTC, datetime

import structlog

from com.qode.qrew.v1.identity.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.models.audit.audit import AuditEvent
from com.qode.qrew.v1.identity.repositories.audit.audit import AuditRepository

logger = structlog.get_logger(__name__)

_ME_PATTERN = "me.{user_id}"


class AuditService:
    """Forwards audit events to the message broker and fans out real-time notifications to connected users."""

    async def record(
        self,
        action: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        ip_address: str | None = None,
        device_fingerprint_hash: str | None = None,
        user_agent: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        now = datetime.now(UTC)
        try:
            from common.broker.publisher import publish as nats_publish  # type: ignore[import-not-found]
            from common.events.envelope import EventEnvelope  # type: ignore[import-not-found]

            envelope = EventEnvelope(
                occurred_at=now,
                aggregate_type=entity_type or "system",
                aggregate_id=entity_id or "",
                actor_id=str(actor_id) if actor_id else None,
                data={
                    "action": str(action),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "ip_address": ip_address,
                    "device_fingerprint_hash": device_fingerprint_hash,
                    "user_agent": user_agent,
                    "payload": payload or {},
                },
            )
            await nats_publish("audit.events.v1", envelope)
        except Exception as exc:
            await logger.awarning("audit_publish_failed", action=action, error=repr(exc))
        if actor_id is not None:
            channel_key = _ME_PATTERN.format(user_id=str(actor_id))
            try:
                from common.broker.publisher import publish as nats_publish  # type: ignore[import-not-found]
                from common.events.envelope import EventEnvelope  # type: ignore[import-not-found]

                ws_envelope = EventEnvelope(
                    occurred_at=now,
                    aggregate_type="ws_fanout",
                    aggregate_id=channel_key,
                    actor_id=str(actor_id),
                    data={
                        "channel": channel_key,
                        "payload": {
                            "type": "audit_event_created",
                            "action": str(action),
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "created_at": now.isoformat(),
                        },
                    },
                )
                await nats_publish("ws.fanout.v1", ws_envelope)
            except Exception as exc:
                await logger.awarning("ws_fanout_publish_failed", action=action, error=repr(exc))

    async def get_recent_login_events(self, user_id: uuid.UUID, limit: int = 5) -> list[AuditEvent]:
        """Returns the most recent successful login events for a given user."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            return await repo.get_recent_login_events(user_id, limit)
