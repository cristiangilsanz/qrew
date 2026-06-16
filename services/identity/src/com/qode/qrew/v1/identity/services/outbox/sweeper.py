from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.database import AsyncSessionLocal
from com.qode.qrew.v1.identity.worker.jobs.enqueue import enqueue as default_enqueue
from observability import traced
from com.qode.qrew.v1.identity.services.outbox.model import OutboxEvent
from com.qode.qrew.v1.identity.core.config import settings

DLQ_UNKNOWN_JOB = "unknown_job_name"

logger = structlog.get_logger(__name__)

EnqueueFn = Callable[[str, dict[str, Any]], Awaitable[Any]]


def _backoff_delay_seconds(attempt: int) -> int:
    """Pick the next backoff window based on the attempt count."""
    delays = settings.outbox_backoff_delays_seconds
    if not delays:
        return 60
    index = min(max(attempt - 1, 0), len(delays) - 1)
    return delays[index]


async def _select_batch(session: AsyncSession, batch_size: int) -> list[OutboxEvent]:
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.dispatched_at.is_(None))
        .where(OutboxEvent.next_attempt_at <= datetime.now(UTC))
        .order_by(OutboxEvent.next_attempt_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@traced("outbox.drain")
async def drain_once(
    *,
    batch_size: int | None = None,
    enqueue_fn: EnqueueFn | None = None,
) -> int:
    """Pull one batch of pending outbox rows and enqueue each."""
    enqueue_target = enqueue_fn or default_enqueue
    limit = batch_size if batch_size is not None else settings.outbox_batch_size
    drained = 0
    async with AsyncSessionLocal() as session, session.begin():
        rows = await _select_batch(session, limit)
        for row in rows:
            try:
                await enqueue_target(row.job_name, dict(row.payload))
                row.dispatched_at = datetime.now(UTC)
                row.last_error = None
                drained += 1
            except KeyError as exc:
                row.attempt_count += 1
                row.last_error = repr(exc)
                if row.attempt_count >= settings.outbox_max_attempts:
                    row.dispatched_at = datetime.now(UTC)
                    row.dlq_reason = DLQ_UNKNOWN_JOB
                    await logger.aerror(
                        "outbox.dlq.unknown_job_name",
                        outbox_id=str(row.id),
                        job_name=row.job_name,
                    )
                else:
                    row.next_attempt_at = datetime.now(UTC) + timedelta(
                        seconds=_backoff_delay_seconds(row.attempt_count)
                    )
            except Exception as exc:  # noqa: BLE001
                row.attempt_count += 1
                row.last_error = repr(exc)
                row.next_attempt_at = datetime.now(UTC) + timedelta(
                    seconds=_backoff_delay_seconds(row.attempt_count)
                )
                if row.attempt_count >= settings.outbox_max_attempts:
                    await logger.aerror(
                        "outbox_row_stuck",
                        outbox_id=str(row.id),
                        job_name=row.job_name,
                        attempts=row.attempt_count,
                        last_error=row.last_error,
                    )
                else:
                    await logger.awarning(
                        "outbox_dispatch_failed",
                        outbox_id=str(row.id),
                        job_name=row.job_name,
                        attempts=row.attempt_count,
                        last_error=row.last_error,
                    )
    if drained:
        await logger.ainfo("outbox_drained", count=drained)
    return drained
