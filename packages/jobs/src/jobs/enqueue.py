from typing import Any

from arq.connections import RedisSettings
from arq.jobs import Job
from observability import CARRIER_KEY, inject_current_context

from jobs.pool import get_pool
from jobs.registry import get_spec


async def enqueue(
    job_name: str,
    payload: dict[str, Any] | None = None,
    *,
    redis_settings: RedisSettings,
    defer_seconds: int | None = None,
) -> Job | None:
    """Enqueues a registered job, propagating the current trace context."""
    spec = get_spec(job_name)
    pool = await get_pool(redis_settings)
    body = dict(payload or {})
    carrier = inject_current_context()
    if carrier and CARRIER_KEY not in body:
        body[CARRIER_KEY] = carrier
    return await pool.enqueue_job(spec.name, body, _defer_by=defer_seconds)
