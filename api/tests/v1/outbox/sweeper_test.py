from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from com.qode.qrew.v1.service.core.outbox import drain_once, sweeper as sweeper_module
from com.qode.qrew.v1.service.core.outbox.model import OutboxEvent
from com.qode.qrew.v1.service.settings import settings


class _FakeSession:
    """A minimal AsyncSession stand-in that returns a fixed batch of rows."""

    def __init__(self, rows: list[OutboxEvent]) -> None:
        self._rows = rows
        self.committed = False
        self.flushed = False

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def begin(self) -> "_FakeSession":
        return self

    async def execute(self, *_args: object, **_kwargs: object) -> "_FakeResult":
        return _FakeResult(self._rows)

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True


class _FakeResult:
    def __init__(self, rows: list[OutboxEvent]) -> None:
        self._rows = rows

    def scalars(self) -> "_FakeScalars":
        return _FakeScalars(self._rows)


class _FakeScalars:
    def __init__(self, rows: list[OutboxEvent]) -> None:
        self._rows = rows

    def all(self) -> list[OutboxEvent]:
        return self._rows


def _make_row(job_name: str = "notification.deliver", attempts: int = 0) -> OutboxEvent:
    row = OutboxEvent(
        aggregate_type="payment",
        aggregate_id="agg-1",
        job_name=job_name,
        payload={"x": 1},
    )
    row.attempt_count = attempts
    row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    return row


async def test_drain_marks_dispatched_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [_make_row(), _make_row()]
    session = _FakeSession(rows)
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)
    enqueue_mock = AsyncMock()

    drained = await drain_once(enqueue_fn=enqueue_mock)
    assert drained == 2
    assert all(r.dispatched_at is not None for r in rows)
    assert enqueue_mock.await_count == 2


async def test_drain_increments_attempt_on_enqueue_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _make_row()
    session = _FakeSession([row])
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)

    async def _broken(_name: str, _payload: dict[str, Any]) -> None:
        raise RuntimeError("redis down")

    drained = await drain_once(enqueue_fn=_broken)
    assert drained == 0
    assert row.dispatched_at is None
    assert row.attempt_count == 1
    assert row.last_error is not None
    assert row.next_attempt_at > datetime.now(UTC)


async def test_drain_marks_row_stuck_at_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _make_row(attempts=settings.outbox_max_attempts - 1)
    session = _FakeSession([row])
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)

    async def _broken(_name: str, _payload: dict[str, Any]) -> None:
        raise RuntimeError("permanent")

    await drain_once(enqueue_fn=_broken)
    assert row.attempt_count == settings.outbox_max_attempts
    assert row.dispatched_at is None


async def test_empty_batch_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession([])
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)
    drained = await drain_once(enqueue_fn=AsyncMock())
    assert drained == 0


def test_backoff_delay_grows_with_attempt_count() -> None:
    delays = [
        sweeper_module._backoff_delay_seconds(n)  # pyright: ignore[reportPrivateUsage]
        for n in range(1, 7)
    ]
    assert delays[0] < delays[1] < delays[2]
    assert delays[-1] == settings.outbox_backoff_delays_seconds[-1]
