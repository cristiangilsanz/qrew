from __future__ import annotations

import structlog
from contracts.envelope import EventEnvelope

from broker.client import get_nats

logger = structlog.get_logger(__name__)


async def publish(subject: str, event: EventEnvelope) -> None:
    """Publishes a domain event to the message broker."""
    payload = event.model_dump_json().encode()
    js = get_nats().js
    ack = await js.publish(subject, payload)
    await logger.adebug(
        "nats.published",
        subject=subject,
        event_id=str(event.event_id),
        seq=ack.seq,
    )
