import uuid

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.core.locking import LockUnavailableError, redlock
from com.qode.qrew.v1.sales.core.queue.queue import admit_batch

logger = structlog.get_logger(__name__)

_ACTIVE_QUEUES = text(
    """
    SELECT event_id, queue_admit_rate_per_minute
    FROM sales.event_context
    WHERE status = 'published'
      AND queue_required = true
      AND sale_ends_at > now()
    """
)


async def admit_next() -> int:
    """Admit one minute's worth of users per active queue. Returns total admitted."""
    admitted_total = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(_ACTIVE_QUEUES)
        rows = list(result.mappings())
    for row in rows:
        event_id = uuid.UUID(str(row["event_id"]))
        batch_size = int(row["queue_admit_rate_per_minute"])
        try:
            async with redlock(f"event:{event_id}:admit", ttl_seconds=30):
                admitted = await admit_batch(event_id=event_id, batch_size=batch_size)
        except LockUnavailableError:
            continue
        admitted_total += len(admitted)
    await logger.ainfo("queue.admit_next", admitted=admitted_total)
    return admitted_total
