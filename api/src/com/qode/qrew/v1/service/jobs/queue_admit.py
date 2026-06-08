import uuid
from typing import Any

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.core.locking import redlock
from com.qode.qrew.v1.service.core.locking.errors import LockUnavailableError
from com.qode.qrew.v1.service.core.queue import admit_batch
from com.qode.qrew.v1.service.core.ws import publish
from com.qode.qrew.v1.service.realtime.queue_channel import queue_channel_key

logger = structlog.get_logger(__name__)

_ACTIVE_EVENTS = text(
    """
    SELECT id, queue_admit_rate_per_minute
    FROM events
    WHERE status = 'published'
      AND queue_required = true
      AND sale_ends_at > now()
    """
)


@job(name="queue.admit_next", cron="* * * * *", max_attempts=1)
async def admit_next(ctx: dict[str, Any]) -> dict[str, Any]:
    """Admit one minute's worth of users per active queue and publish tokens."""
    del ctx
    admitted_total = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(_ACTIVE_EVENTS)
        rows = list(result.mappings())
    for row in rows:
        event_id = uuid.UUID(str(row["id"]))
        batch_size = int(row["queue_admit_rate_per_minute"])
        try:
            async with redlock(f"event:{event_id}:admit", ttl_seconds=30):
                admitted = await admit_batch(event_id=event_id, batch_size=batch_size)
        except LockUnavailableError:
            continue
        for slot in admitted:
            await publish(
                queue_channel_key(str(event_id), slot.user_id),
                {
                    "type": "queue.admitted",
                    "event_id": str(event_id),
                    "redeem_window_token": slot.redeem_token,
                    "jti": slot.jti,
                },
            )
        admitted_total += len(admitted)
    await logger.ainfo("queue.admit_next", admitted=admitted_total)
    return {"admitted": admitted_total}
