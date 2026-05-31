import json
from typing import Any

import fakeredis.aioredis
import pytest
from arq.worker import Retry

from com.qode.qrew.v1.service.core.jobs.context import wrap_handler
from com.qode.qrew.v1.service.core.jobs.dlq import dlq_key
from com.qode.qrew.v1.service.core.jobs.registry import JobSpec


def _spec(handler: Any, max_attempts: int = 3) -> JobSpec:
    return JobSpec(
        name="test.unit",
        handler=handler,
        max_attempts=max_attempts,
        retry_delays=(1, 2, 4, 8, 16),
        cron_fields=None,
    )


async def test_runs_handler_on_first_attempt() -> None:
    calls: list[int] = []

    async def handler(ctx: dict[str, Any]) -> str:
        calls.append(int(ctx["job_try"]))
        return "ok"

    runner = wrap_handler(_spec(handler))
    redis = fakeredis.aioredis.FakeRedis()
    result = await runner({"job_try": 1, "job_id": "j1", "redis": redis})
    assert result == "ok"
    assert calls == [1]


async def test_raises_retry_on_failure_below_max() -> None:
    async def handler(ctx: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    runner = wrap_handler(_spec(handler, max_attempts=3))
    redis = fakeredis.aioredis.FakeRedis()
    with pytest.raises(Retry) as info:
        await runner({"job_try": 1, "job_id": "j1", "redis": redis})
    assert info.value.defer_score is not None


async def test_dead_letters_on_final_attempt() -> None:
    async def handler(ctx: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    runner = wrap_handler(_spec(handler, max_attempts=3))
    redis = fakeredis.aioredis.FakeRedis()
    result = await runner({"job_try": 3, "job_id": "j1", "redis": redis})
    assert result is None
    entries_raw: Any = await redis.lrange(dlq_key("test.unit"), 0, -1)  # type: ignore[misc]
    entries: list[bytes] = list(entries_raw)  # pyright: ignore[reportUnknownArgumentType]
    assert len(entries) == 1
    parsed = json.loads(entries[0])
    assert parsed["job_id"] == "j1"
    assert "boom" in parsed["error"]
