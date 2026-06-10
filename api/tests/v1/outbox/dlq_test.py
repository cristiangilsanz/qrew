from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from com.qode.qrew.v1.service.core.outbox import drain_once
from com.qode.qrew.v1.service.core.outbox import sweeper as sweeper_module
from com.qode.qrew.v1.service.core.outbox.model import OutboxEvent
from com.qode.qrew.v1.service.core.outbox.sweeper import DLQ_UNKNOWN_JOB
from com.qode.qrew.v1.service.settings import settings


class _FakeSession:
    def __init__(self, rows: list[OutboxEvent]) -> None:
        self._rows = rows

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def begin(self) -> "_FakeSession":
        return self

    async def execute(self, *_args: object, **_kwargs: object) -> Any:
        class _R:
            def __init__(self, rows: list[OutboxEvent]) -> None:
                self._rows = rows

            def scalars(self) -> Any:
                rows = self._rows

                class _S:
                    def all(self) -> list[OutboxEvent]:
                        return rows

                return _S()

        return _R(self._rows)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


def _row(job_name: str, attempts: int = 0) -> OutboxEvent:
    row = OutboxEvent(
        aggregate_type="agg", aggregate_id="x", job_name=job_name, payload={}
    )
    row.attempt_count = attempts
    row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    return row


async def test_unknown_job_dlqs_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _row(
        "notifications.does_not_exist", attempts=settings.outbox_max_attempts - 1
    )
    session = _FakeSession([row])
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)

    async def _enqueue(name: str, _payload: dict[str, Any]) -> None:
        # mirror the real enqueue() — raises KeyError on unknown job names.
        from com.qode.qrew.v1.service.core.jobs.registry import get_spec

        get_spec(name)

    await drain_once(enqueue_fn=_enqueue)
    assert row.dispatched_at is not None
    assert row.dlq_reason == DLQ_UNKNOWN_JOB


async def test_unknown_job_retries_before_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _row("notifications.does_not_exist", attempts=0)
    session = _FakeSession([row])
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)

    async def _enqueue(name: str, _payload: dict[str, Any]) -> None:
        from com.qode.qrew.v1.service.core.jobs.registry import get_spec

        get_spec(name)

    await drain_once(enqueue_fn=_enqueue)
    assert row.dispatched_at is None
    assert row.dlq_reason is None
    assert row.attempt_count == 1


async def test_known_job_unaffected_by_dlq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _row("notifications.payment_succeeded")
    session = _FakeSession([row])
    monkeypatch.setattr(sweeper_module, "AsyncSessionLocal", lambda: session)

    async def _enqueue(name: str, _payload: dict[str, Any]) -> None:
        del name
        return None

    drained = await drain_once(enqueue_fn=_enqueue)
    assert drained == 1
    assert row.dispatched_at is not None
    assert row.dlq_reason is None
