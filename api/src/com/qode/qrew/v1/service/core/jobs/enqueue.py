from typing import Any

from arq.jobs import Job

from com.qode.qrew.v1.service.core.jobs.pool import get_pool
from com.qode.qrew.v1.service.core.jobs.registry import get_spec


async def enqueue(
    job_name: str,
    payload: dict[str, Any] | None = None,
    *,
    defer_seconds: int | None = None,
) -> Job | None:
    """Enqueue a registered job for asynchronous execution."""
    spec = get_spec(job_name)
    pool = await get_pool()
    return await pool.enqueue_job(
        spec.name,
        payload or {},
        _defer_by=defer_seconds,
    )
