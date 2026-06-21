import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from com.qode.qrew.v1.entry.models.projections import TicketState
from com.qode.qrew.v1.entry.services.application.entry.entry_stats import (
    _deserialise,
    _resolve_since,
    _stats_cache_key,
    compute_entry_stats,
)
from com.qode.qrew.v1.entry.services.domain.entry import EntryStats

_PATCH_SETTINGS = "com.qode.qrew.v1.entry.services.application.entry.entry_stats.settings"


def _make_redis(*, cached: str | bytes | None = None) -> MagicMock:
    redis = MagicMock()
    redis.get = AsyncMock(return_value=cached)
    redis.set = AsyncMock()
    return redis


def _make_db(
    *,
    state_rows: list[tuple[str, int]] | None = None,
    rejection_rows: list[tuple[str, int]] | None = None,
    last_scan: datetime | None = None,
) -> MagicMock:
    """Mock AsyncSession that returns provided rows for execute() calls."""
    state_rows = state_rows or []
    rejection_rows = rejection_rows or []

    call_count = 0

    async def _execute(_query):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        # First call → state counts; second call → rejection counts
        mock_result.all.return_value = state_rows if call_count == 1 else rejection_rows
        return mock_result

    async def _scalar(_query):  # type: ignore[no-untyped-def]
        return last_scan

    db = MagicMock()
    db.execute = _execute
    db.scalar = _scalar
    return db


def _fake_settings(
    *,
    window_hours: int = 24,
    cache_ttl: int = 30,
) -> MagicMock:
    s = MagicMock()
    s.entry_stats_default_window_hours = window_hours
    s.entry_stats_cache_ttl_seconds = cache_ttl
    return s


class TestResolveSince:
    def test_returns_provided_datetime(self) -> None:
        fixed = datetime(2026, 6, 1, tzinfo=UTC)
        with patch(_PATCH_SETTINGS, _fake_settings()):
            result = _resolve_since(fixed)
        assert result == fixed

    def test_defaults_to_window_hours_ago(self) -> None:
        before = datetime.now(UTC)
        with patch(_PATCH_SETTINGS, _fake_settings(window_hours=12)):
            result = _resolve_since(None)
        after = datetime.now(UTC)
        expected_approx = before - timedelta(hours=12)
        assert expected_approx <= result <= after


class TestDeserialise:
    def test_round_trip_payload(self) -> None:
        event_id = uuid.uuid4()
        since = datetime(2026, 6, 1, tzinfo=UTC)
        last_scan = datetime(2026, 6, 2, 10, tzinfo=UTC)
        stats = EntryStats(
            event_id=event_id,
            since=since,
            total_issued=100,
            total_entered=40,
            total_remaining=60,
            rejections_by_reason={"signature": 3, "replay": 1},
            last_scan_at=last_scan,
        )
        raw = json.dumps(stats.to_payload())
        result = _deserialise(raw, event_id, since)
        assert result.total_issued == 100
        assert result.total_entered == 40
        assert result.total_remaining == 60
        assert result.rejections_by_reason == {"signature": 3, "replay": 1}
        assert result.last_scan_at == last_scan

    def test_handles_missing_last_scan(self) -> None:
        event_id = uuid.uuid4()
        since = datetime(2026, 6, 1, tzinfo=UTC)
        raw = json.dumps(
            {"total_issued": 5, "total_entered": 2, "total_remaining": 3}
        )
        result = _deserialise(raw, event_id, since)
        assert result.last_scan_at is None


class TestComputeEntryStats:
    async def test_returns_cached_when_redis_hit(self, event_id: uuid.UUID) -> None:
        since = datetime(2026, 6, 1, tzinfo=UTC)
        payload = json.dumps(
            {
                "event_id": str(event_id),
                "since": since.isoformat(),
                "total_issued": 50,
                "total_entered": 20,
                "total_remaining": 30,
                "rejections_by_reason": {"signature": 1},
            }
        )
        redis = _make_redis(cached=payload)
        db = MagicMock()

        with patch(_PATCH_SETTINGS, _fake_settings()):
            result = await compute_entry_stats(db, redis, event_id=event_id, since=since)

        assert result.total_issued == 50
        assert result.total_entered == 20
        db.execute.assert_not_called()

    async def test_queries_db_on_cache_miss(self, event_id: uuid.UUID) -> None:
        since = datetime(2026, 6, 1, tzinfo=UTC)
        redis = _make_redis(cached=None)
        db = _make_db(
            state_rows=[
                (TicketState.issued.value, 80),
                (TicketState.used.value, 30),
                (TicketState.entry_pending.value, 5),
            ],
            rejection_rows=[("signature", 4), ("replay", 2)],
            last_scan=datetime(2026, 6, 2, tzinfo=UTC),
        )
        with patch(_PATCH_SETTINGS, _fake_settings(cache_ttl=60)):
            result = await compute_entry_stats(db, redis, event_id=event_id, since=since)

        assert result.total_issued == 115   # 80 + 30 + 5
        assert result.total_entered == 30   # only "used" count
        assert result.total_remaining == 85
        assert result.rejections_by_reason["signature"] == 4
        assert result.rejections_by_reason["replay"] == 2
        redis.set.assert_awaited_once()

    async def test_cache_write_failure_is_swallowed(self, event_id: uuid.UUID) -> None:
        since = datetime(2026, 6, 1, tzinfo=UTC)
        redis = _make_redis(cached=None)
        redis.set = AsyncMock(side_effect=RuntimeError("redis down"))
        db = _make_db()
        with patch(_PATCH_SETTINGS, _fake_settings()):
            result = await compute_entry_stats(db, redis, event_id=event_id, since=since)
        assert isinstance(result, EntryStats)

    async def test_remaining_never_goes_negative(self, event_id: uuid.UUID) -> None:
        since = datetime(2026, 6, 1, tzinfo=UTC)
        redis = _make_redis(cached=None)
        # More entered than issued (data anomaly)
        db = _make_db(
            state_rows=[(TicketState.used.value, 100)],
        )
        with patch(_PATCH_SETTINGS, _fake_settings()):
            result = await compute_entry_stats(db, redis, event_id=event_id, since=since)
        assert result.total_remaining == 0
