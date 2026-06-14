import uuid
from datetime import UTC, datetime

import structlog

from com.qode.qrew.v1.identity.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.core.ws import publish as ws_publish
from com.qode.qrew.v1.identity.models.audit.audit import AuditEvent
from com.qode.qrew.v1.identity.realtime import me_channel_key
from com.qode.qrew.v1.identity.repositories.audit.audit import AuditRepository

logger = structlog.get_logger(__name__)


class AuditService:
    """Publishes audit events to NATS audit.events.v1 for the audit service to chain."""

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
            await ws_publish(
                me_channel_key(str(actor_id)),
                {
                    "type": "audit_event_created",
                    "action": str(action),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "created_at": now.isoformat(),
                },
            )

    async def get_recent_login_events(self, user_id: uuid.UUID, limit: int = 5) -> list[AuditEvent]:
        """List the most recent successful logins for a user (direct DB read)."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            return await repo.get_recent_login_events(user_id, limit)
