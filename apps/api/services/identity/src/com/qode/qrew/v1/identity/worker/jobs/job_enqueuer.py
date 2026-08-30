# enqueues a named job onto the shared arq queue carrying the trace context
from typing import Any

from arq.jobs import Job

from db.redis import redis_settings_from_url
from jobs import get_pool, get_spec
from observability import CARRIER_KEY, inject_current_context
from com.qode.qrew.v1.identity.core.config import settings

QUEUE_NAME = "qrew:jobs:identity"


# enqueues a job with its trace context attached
async def enqueue(
    job_name: str,
    payload: dict[str, Any] | None = None,
    *,
    defer_seconds: int | None = None,
) -> Job | None:
    spec = get_spec(job_name)
    pool = await get_pool(redis_settings_from_url(settings.redis_url))
    body = dict(payload or {})
    carrier = inject_current_context()
    if carrier and CARRIER_KEY not in body:
        body[CARRIER_KEY] = carrier
    return await pool.enqueue_job(spec.name, body, _defer_by=defer_seconds, _queue_name=QUEUE_NAME)
