import json
import traceback
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis


def dlq_key(job_name: str) -> str:
    return f"dlq:{job_name}"


async def push_to_dlq(
    redis_client: aioredis.Redis,  # type: ignore[type-arg]
    *,
    job_name: str,
    job_id: str,
    payload: dict[str, Any],
    error: BaseException,
) -> None:
    """Record a job that exhausted its retry budget."""
    entry = {
        "job_id": job_id,
        "job_name": job_name,
        "payload": payload,
        "error": repr(error),
        "traceback": "".join(traceback.format_exception(error)),
        "failed_at": datetime.now(UTC).isoformat(),
    }
    await redis_client.lpush(dlq_key(job_name), json.dumps(entry))  # type: ignore[misc]
