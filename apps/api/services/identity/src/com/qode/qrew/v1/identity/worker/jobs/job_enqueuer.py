from typing import Any

from arq.jobs import Job

from db.redis import redis_settings_from_url
from jobs import get_pool, get_spec
from observability import CARRIER_KEY, inject_current_context
from com.qode.qrew.v1.identity.core.config import settings


async def enqueue(
    job_name: str,
    payload: dict[str, Any] | None = None,
    *,
    defer_seconds: int | None = None,
) -> Job | None:
    """Enqueue a registered job, propagating the current trace context."""
    spec = get_spec(job_name)
    pool = await get_pool(redis_settings_from_url(settings.redis_url))
    body = dict(payload or {})
    carrier = inject_current_context()
    if carrier and CARRIER_KEY not in body:
        body[CARRIER_KEY] = carrier
    return await pool.enqueue_job(spec.name, body, _defer_by=defer_seconds)
