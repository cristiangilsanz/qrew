# wakes the outbox drainer as soon as the transaction that recorded an event commits
import asyncio
from typing import Any

import structlog
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

# marks a session that recorded an event, so only those sessions wake the drainer
PENDING_KEY = "outbox_pending"

# keeps a strong reference to every in flight notification, so none is garbage collected
_tasks: set[asyncio.Task[None]] = set()

# remembers the drainers already wired, so a second install does not double the listener
_installed: set[str] = set()


# marks the session so the listener knows this transaction carries an event
def mark_pending(session: Any) -> None:
    # a session without the mapping carries no listener either, and the notice is
    # only ever a hint, so recording the event must not fail for want of one
    info: Any = getattr(session, "info", None)
    if isinstance(info, dict):
        info[PENDING_KEY] = True  # pyright: ignore[reportUnknownMemberType]


# enqueues the drain job, swallowing any failure because the cron stays the safety net
async def _enqueue_drain(job_name: str, queue_name: str, redis_url: str) -> None:
    try:
        from db.redis import redis_settings_from_url
        from jobs import enqueue

        await enqueue(
            job_name,
            redis_settings=redis_settings_from_url(redis_url),
            queue_name=queue_name,
        )
    except Exception as exc:
        await logger.awarning("outbox.notify_failed", job=job_name, error=repr(exc))


# schedules the notification without holding up the transaction that just committed
def _schedule(job_name: str, queue_name: str, redis_url: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning("outbox.notify_no_loop", job=job_name)
        return
    task = loop.create_task(_enqueue_drain(job_name, queue_name, redis_url))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


# wires the after commit hook that wakes this service's drainer once per transaction
def install_drain_notifier(
    service: str, *, redis_url: str, job_name: str | None = None
) -> None:
    name = job_name or f"{service}.outbox.drain"
    if name in _installed:
        return
    _installed.add(name)
    queue_name = f"qrew:jobs:{service}"

    # notifies the drainer after the transaction that recorded the event commits
    @event.listens_for(Session, "after_commit")
    def _on_commit(session: Session) -> None:
        if not session.info.pop(PENDING_KEY, False):
            return
        _schedule(name, queue_name, redis_url)

    # drops the mark, so a rolled back transaction never wakes the drainer
    @event.listens_for(Session, "after_rollback")
    def _on_rollback(session: Session) -> None:
        session.info.pop(PENDING_KEY, None)

    # drops the mark left by a transaction that never reached the database
    @event.listens_for(Session, "after_soft_rollback")
    def _on_soft_rollback(session: Session, previous_transaction: Any) -> None:
        del previous_transaction
        if not session.in_transaction():
            session.info.pop(PENDING_KEY, None)
