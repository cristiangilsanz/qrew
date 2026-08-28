# writes an outbox row in the same transaction as the change it announces
from typing import Any

import structlog
from opentelemetry import propagate, trace
from sqlalchemy.ext.asyncio import AsyncSession

from observability import traced
from com.qode.qrew.v1.identity.models.outbox import OutboxEvent

logger = structlog.get_logger(__name__)


# writes an outbox row carrying the current trace context
@traced("outbox.publish")
async def publish_via_outbox(
    session: AsyncSession,
    *,
    aggregate_type: str,
    aggregate_id: str,
    job_name: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    enriched = dict(payload)
    span = trace.get_current_span()
    if span.get_span_context().is_valid:
        carrier: dict[str, str] = {}
        propagate.inject(carrier)
        enriched["_otel"] = carrier
    row = OutboxEvent(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        job_name=job_name,
        payload=enriched,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    await logger.ainfo(
        "outbox_published",
        outbox_id=str(row.id),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        job_name=job_name,
    )
    return row
