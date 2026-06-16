from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def publish_audit_event(
    *,
    subject: str,
    aggregate_type: str,
    aggregate_id: str,
    actor_id: str | None,
    data: dict[str, Any],
) -> None:
    """Publish a structured audit event using the service's shared NATS connection."""
    try:
        from broker.client import get_nats
        from contracts.envelope import EventEnvelope

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor_id=actor_id,
            data=data,
        )
        nc = get_nats()
        await nc.js.publish(subject, envelope.model_dump_json().encode())
    except Exception as exc:
        await logger.awarning(
            "audit_publisher.publish_failed",
            subject=subject,
            aggregate_type=aggregate_type,
            error=repr(exc),
        )
