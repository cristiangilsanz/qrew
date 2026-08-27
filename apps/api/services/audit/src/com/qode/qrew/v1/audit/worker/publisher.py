# publishes an audit event envelope onto the shared nats connection
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

AUDIT_EVENTS_SUBJECT = "audit.events.v1"


# builds an envelope and publishes it to the given subject
async def publish_audit_event(
    *,
    subject: str,
    aggregate_type: str,
    aggregate_id: str,
    actor_id: str | None,
    data: dict[str, Any],
) -> None:
    try:
        from contracts.messaging.envelope import EventEnvelope
        from messaging.client import get_nats

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
            "auditor.publish_failed",
            subject=subject,
            aggregate_type=aggregate_type,
            error=repr(exc),
        )
