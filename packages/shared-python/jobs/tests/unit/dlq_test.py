import json
from unittest.mock import AsyncMock, MagicMock

from jobs.dlq import dlq_key, push_to_dlq


class TestDlqKey:
    def test_format(self) -> None:
        assert dlq_key("my.job") == "dlq:my.job"

    def test_different_names_differ(self) -> None:
        assert dlq_key("job.a") != dlq_key("job.b")


class TestPushToDlq:
    async def test_pushes_json_entry(self) -> None:
        redis = MagicMock()
        redis.lpush = AsyncMock()
        error = ValueError("something broke")
        await push_to_dlq(
            redis,
            job_name="my.job",
            job_id="job-123",
            payload={"x": 1},
            error=error,
        )
        redis.lpush.assert_awaited_once()
        key, raw = redis.lpush.call_args.args
        assert key == "dlq:my.job"
        entry = json.loads(raw)
        assert entry["job_id"] == "job-123"
        assert entry["job_name"] == "my.job"
        assert "ValueError" in entry["error"]
        assert "failed_at" in entry

    async def test_payload_is_stored(self) -> None:
        redis = MagicMock()
        redis.lpush = AsyncMock()
        await push_to_dlq(
            redis,
            job_name="job",
            job_id="id",
            payload={"amount": 100, "currency": "EUR"},
            error=RuntimeError("oops"),
        )
        _, raw = redis.lpush.call_args.args
        entry = json.loads(raw)
        assert entry["payload"]["amount"] == 100
