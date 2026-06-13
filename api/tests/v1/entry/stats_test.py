import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest_asyncio

from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.ticket import TicketState
from com.qode.qrew.v1.service.services.entry_stats import compute_entry_stats


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


def _session_with(
    *,
    state_counts: dict[str, int],
    rejection_counts: dict[str, int],
    last_validated: datetime | None = None,
    last_rejected: datetime | None = None,
) -> MagicMock:
    """Build a session whose executes return the listed counts in order."""
    db = MagicMock()
    state_rows = [(TicketState(s), c) for s, c in state_counts.items()]
    rejection_rows = list(rejection_counts.items())
    last_scans = [last_validated, last_rejected]
    executes: list[Any] = []

    async def _execute(*_args: Any, **_kwargs: Any) -> Any:
        idx = len(executes)
        executes.append(idx)
        result = MagicMock()
        if idx == 0:
            result.all = MagicMock(return_value=state_rows)
        elif idx == 1:
            result.all = MagicMock(return_value=rejection_rows)
        else:
            result.all = MagicMock(return_value=[])
        return result

    async def _scalar(*_args: Any, **_kwargs: Any) -> Any:
        if last_scans:
            return last_scans.pop(0)
        return None

    db.execute = AsyncMock(side_effect=_execute)
    db.scalar = AsyncMock(side_effect=_scalar)
    return db


async def test_compute_entry_stats_rolls_up_counts(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    db = _session_with(
        state_counts={
            TicketState.issued.value: 7,
            TicketState.used.value: 5,
            TicketState.cancelled.value: 1,
        },
        rejection_counts={"signature": 2, "replay": 3, "state": 1},
    )
    stats = await compute_entry_stats(db, redis_client, event_id=event_id)
    assert stats.total_issued == 12  # issued + used (cancelled excluded)
    assert stats.total_entered == 5
    assert stats.total_remaining == 7
    assert stats.rejections_by_reason["signature"] == 2
    assert stats.rejections_by_reason["replay"] == 3
    assert stats.rejections_by_reason["state"] == 1
    assert stats.rejections_by_reason["audience"] == 0


async def test_compute_entry_stats_caches_within_ttl(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    db = _session_with(
        state_counts={TicketState.issued.value: 3},
        rejection_counts={},
    )
    first = await compute_entry_stats(db, redis_client, event_id=event_id)
    second = await compute_entry_stats(db, redis_client, event_id=event_id)
    assert first.total_issued == second.total_issued == 3
    assert db.execute.await_count == 2


async def test_compute_entry_stats_returns_last_scan_at(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    last = datetime(2026, 7, 1, 19, 30, tzinfo=UTC)
    earlier = last - timedelta(minutes=5)
    db = _session_with(
        state_counts={TicketState.used.value: 1},
        rejection_counts={"replay": 1},
        last_validated=last,
        last_rejected=earlier,
    )
    stats = await compute_entry_stats(db, redis_client, event_id=event_id)
    assert stats.last_scan_at == last


async def test_payload_serialisation_round_trips(redis_client: Any) -> None:
    event_id = uuid.uuid4()
    db = _session_with(
        state_counts={TicketState.used.value: 2, TicketState.issued.value: 4},
        rejection_counts={"signature": 1},
    )
    first = await compute_entry_stats(db, redis_client, event_id=event_id)
    again = await compute_entry_stats(db, redis_client, event_id=event_id)
    assert first.total_entered == again.total_entered
    assert first.rejections_by_reason == again.rejections_by_reason


def test_audit_action_constants_present() -> None:
    assert AuditAction.ENTRY_VALIDATED.value == "entry_validated"
    assert AuditAction.ENTRY_REJECTED.value == "entry_rejected"
