import uuid

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.sales.core.database import AsyncSessionLocal
from locking import LockUnavailableError, redlock
from com.qode.qrew.v1.sales.services.application.queue.storage import admit_batch
from com.qode.qrew.v1.sales.core.config import settings

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
    """Admits a batch of waiting users into each active queue and returns the total count admitted."""
    admitted_total = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(_ACTIVE_QUEUES)
        rows = list(result.mappings())
    for row in rows:
        event_id = uuid.UUID(str(row["event_id"]))
        batch_size = int(row["queue_admit_rate_per_minute"])
        try:
            async with redlock(
                f"event:{event_id}:admit", redis_url=settings.redis_url, ttl_seconds=30
            ):
                admitted = await admit_batch(event_id=event_id, batch_size=batch_size)
        except LockUnavailableError:
            continue
        admitted_total += len(admitted)
    await logger.ainfo("queue.admit_next", admitted=admitted_total)
    return admitted_total
