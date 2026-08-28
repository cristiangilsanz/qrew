# enqueues a named job carrying the trace context onto the shared arq queue
from typing import Any

from arq.connections import RedisSettings
from arq.jobs import Job
from observability import CARRIER_KEY, inject_current_context

from .pool import get_pool
from .registry import get_spec


# enqueues a job with its trace context attached
async def enqueue(
    job_name: str,
    payload: dict[str, Any] | None = None,
    *,
    redis_settings: RedisSettings,
    defer_seconds: int | None = None,
) -> Job | None:
    spec = get_spec(job_name)
    pool = await get_pool(redis_settings)
    body = dict(payload or {})
    carrier = inject_current_context()
    if carrier and CARRIER_KEY not in body:
        body[CARRIER_KEY] = carrier
    return await pool.enqueue_job(spec.name, body, _defer_by=defer_seconds)
