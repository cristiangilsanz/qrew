from __future__ import annotations

import structlog

from common.broker.client import get_nats
from common.events.envelope import EventEnvelope

logger = structlog.get_logger(__name__)


async def publish(subject: str, event: EventEnvelope) -> None:
    """Publish a domain event to a NATS JetStream subject.

    Subject format: <context>.<aggregate>.<verb>.v<N>
    e.g. payments.payment.succeeded.v1
    """
    payload = event.model_dump_json().encode()
    js = get_nats().js
    ack = await js.publish(subject, payload)
    await logger.adebug(
        "nats.published",
        subject=subject,
        event_id=str(event.event_id),
        seq=ack.seq,
    )
