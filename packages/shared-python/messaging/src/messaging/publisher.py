# publishes an event envelope onto the shared nats connection
from __future__ import annotations

import structlog
from contracts.messaging.envelope import EventEnvelope

from .client import get_nats

logger = structlog.get_logger(__name__)


# publishes an event envelope to a subject
async def publish(subject: str, event: EventEnvelope) -> None:
    payload = event.model_dump_json(by_alias=True).encode()
    js = get_nats().js
    ack = await js.publish(subject, payload)
    await logger.adebug(
        "nats.published",
        subject=subject,
        event_id=str(event.event_id),
        seq=ack.seq,
    )
