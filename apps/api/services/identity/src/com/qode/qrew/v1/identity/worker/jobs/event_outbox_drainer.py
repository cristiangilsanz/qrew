# publishes to the broker every domain event waiting in the outbox
from datetime import UTC
from typing import Any

from contracts.messaging.envelope import EventEnvelope
from jobs import job, parse_crontab
from messaging.publisher import publish
from outbox import drain_once

from com.qode.qrew.v1.identity.core.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.models.event_outbox import EventOutbox


# rebuilds the envelope the broker expects from the row the transaction left
def _envelope(row: Any) -> EventEnvelope:
    return EventEnvelope(
        occurred_at=row.created_at.astimezone(UTC),
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        actor_id=row.actor_id,
        data=row.payload,
    )


# drains the event outbox on a short schedule, so an event never waits long
@job("identity.event_outbox.drain", cron=parse_crontab("* * * * *"), max_attempts=1)
async def drain_event_outbox(ctx: dict[str, Any]) -> dict[str, int]:
    del ctx
    sent = await drain_once(AsyncSessionLocal, EventOutbox, publish, _envelope)
    return {"sent": sent}
