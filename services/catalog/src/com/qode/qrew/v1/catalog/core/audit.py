import uuid
from datetime import UTC, datetime

import structlog

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
        try:
            from common.broker.publisher import publish as nats_publish  # type: ignore[import-not-found]
            from common.events.envelope import EventEnvelope  # type: ignore[import-not-found]

            envelope = EventEnvelope(
                occurred_at=datetime.now(UTC),
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
