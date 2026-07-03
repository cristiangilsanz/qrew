import json
import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
import structlog
from observability import traced
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.core.config import settings
from com.qode.qrew.v1.entry.models.entry_attempt import EntryAttempt
from com.qode.qrew.v1.entry.models.projections import TicketContext, TicketState
from com.qode.qrew.v1.entry.services.domain.entry import EntryStats

logger = structlog.get_logger(__name__)

_REASONS: tuple[str, ...] = (
    "signature",
    "audience",
    "expired",
    "wrong_event",
    "wrong_venue",
    "replay",
    "not_found",
    "wrong_owner",
    "state",
    "busy",
)


def _stats_cache_key(event_id: uuid.UUID, since: datetime) -> str:
    return f"entry:stats:{event_id}:{int(since.timestamp())}"


def _resolve_since(since: datetime | None) -> datetime:
    if since is not None:
        return since
    return datetime.now(UTC) - timedelta(
        hours=settings.entry_stats_default_window_hours
    )


@traced("entry_stats.compute")
async def compute_entry_stats(
    db: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    *,
    event_id: uuid.UUID,
    since: datetime | None = None,
) -> EntryStats:
    since_at = _resolve_since(since)
    key = _stats_cache_key(event_id, since_at)
    cached = await redis.get(key)  # type: ignore[misc]
    if cached is not None:
        return _deserialise(cached, event_id, since_at)
    stats = await _compute_uncached(db, event_id=event_id, since=since_at)
    try:
        await redis.set(  # type: ignore[misc]
            key,
            json.dumps(stats.to_payload()),
            ex=settings.entry_stats_cache_ttl_seconds,
        )
    except Exception as exc:
        await logger.awarning("entry_stats_cache_write_failed", error=repr(exc))
    return stats


async def _compute_uncached(
    db: AsyncSession, *, event_id: uuid.UUID, since: datetime
) -> EntryStats:
    counted_states = {
        TicketState.issued.value,
        TicketState.entry_pending.value,
        TicketState.used.value,
    }
    rows = await db.execute(
        select(TicketContext.state, func.count())
        .where(TicketContext.event_id == event_id)
        .group_by(TicketContext.state)
    )
    counts: dict[str, int] = {}
    for state_value, count in rows.all():
        if isinstance(state_value, str):
            counts[state_value] = int(count)
    total_issued = sum(n for s, n in counts.items() if s in counted_states)
    total_entered = counts.get(TicketState.used.value, 0)
    total_remaining = max(total_issued - total_entered, 0)

    rejection_rows = await db.execute(
        select(EntryAttempt.reason, func.count())
        .where(EntryAttempt.event_id == event_id)
        .where(EntryAttempt.allowed.is_(False))
        .where(EntryAttempt.scanned_at >= since)
        .group_by(EntryAttempt.reason)
    )
    rejections: dict[str, int] = dict.fromkeys(_REASONS, 0)
    for reason, count in rejection_rows.all():
        if isinstance(reason, str) and reason in rejections:
            rejections[reason] = int(count)

    last_scan_at = await db.scalar(
        select(func.max(EntryAttempt.scanned_at)).where(
            EntryAttempt.event_id == event_id
        )
    )

    return EntryStats(
        event_id=event_id,
        since=since,
        total_issued=total_issued,
        total_entered=total_entered,
        total_remaining=total_remaining,
        rejections_by_reason=rejections,
        last_scan_at=last_scan_at,
    )


def _deserialise(raw: str | bytes, event_id: uuid.UUID, since: datetime) -> EntryStats:
    data = json.loads(raw)
    last_raw = data.get("last_scan_at")
    last_scan = datetime.fromisoformat(last_raw) if last_raw else None
    return EntryStats(
        event_id=event_id,
        since=since,
        total_issued=int(data.get("total_issued", 0)),
        total_entered=int(data.get("total_entered", 0)),
        total_remaining=int(data.get("total_remaining", 0)),
        rejections_by_reason=dict(data.get("rejections_by_reason", {})),
        last_scan_at=last_scan,
    )
