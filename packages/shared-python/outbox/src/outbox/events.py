# records domain events inside the caller's transaction and drains them to the broker
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import structlog
from sqlalchemy import DateTime, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

logger = structlog.get_logger(__name__)

# a row that exhausts these attempts is parked instead of retried for ever
MAX_ATTEMPTS = 8
BACKOFF_SECONDS = (5, 15, 60, 300, 900, 1800, 3600)
DLQ_EXHAUSTED = "attempts_exhausted"


class EventOutboxMixin:
    # holds the event until a drainer confirms the broker took it
    __tablename__ = "event_outbox"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dlq_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class _OutboxModel(Protocol):
    id: Any
    subject: Any
    dispatched_at: Any
    attempt_count: Any
    next_attempt_at: Any


# leaves the event in the outbox, so it travels with the change that caused it
async def record(
    session: AsyncSession,
    model: type[Any],
    *,
    subject: str,
    aggregate_type: str,
    aggregate_id: str,
    data: dict[str, Any],
    actor_id: str | None = None,
) -> None:
    session.add(
        model(
            subject=subject,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor_id=actor_id,
            payload=data,
        )
    )


# looks up the wait before the next attempt of a row that keeps failing
def _backoff(attempt: int) -> int:
    index = min(max(attempt - 1, 0), len(BACKOFF_SECONDS) - 1)
    return BACKOFF_SECONDS[index]


# takes a batch of pending rows without letting two drainers claim the same one
async def _claim(session: AsyncSession, model: type[Any], batch_size: int) -> list[Any]:
    stmt = (
        select(model)
        .where(model.dispatched_at.is_(None))
        .where(model.dlq_reason.is_(None))
        .where(model.next_attempt_at <= datetime.now(UTC))
        .order_by(model.next_attempt_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


PublishFn = Callable[[str, Any], Awaitable[None]]


# publishes every pending event and reschedules the ones the broker refuses
async def drain_once(
    session_factory: Callable[[], AsyncSession],
    model: type[Any],
    publish: PublishFn,
    envelope_factory: Callable[[Any], Any],
    *,
    batch_size: int = 50,
) -> int:
    sent = 0
    async with session_factory() as session, session.begin():
        for row in await _claim(session, model, batch_size):
            try:
                await publish(row.subject, envelope_factory(row))
            except Exception as exc:
                row.attempt_count += 1
                row.last_error = repr(exc)[:2000]
                if row.attempt_count >= MAX_ATTEMPTS:
                    row.dlq_reason = DLQ_EXHAUSTED
                    await logger.aerror(
                        "outbox.parked", subject=row.subject, attempts=row.attempt_count
                    )
                else:
                    row.next_attempt_at = datetime.now(UTC) + timedelta(
                        seconds=_backoff(row.attempt_count)
                    )
                continue
            row.dispatched_at = datetime.now(UTC)
            sent += 1
    if sent:
        await logger.ainfo("outbox.drained", events=sent)
    return sent
