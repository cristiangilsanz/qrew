from typing import Any

from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.core.outbox import drain_once


@job(name="outbox.drain", cron="* * * * *", max_attempts=1)
async def drain_outbox(ctx: dict[str, Any]) -> dict[str, int]:
    """Drain a batch of pending outbox rows once per minute."""
    del ctx
    drained = await drain_once()
    return {"drained": drained}
