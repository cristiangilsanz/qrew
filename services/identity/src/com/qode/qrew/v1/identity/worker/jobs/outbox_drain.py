from typing import Any

from com.qode.qrew.v1.identity.worker.jobs.registry import job
from com.qode.qrew.v1.identity.services.outbox import drain_once


@job(name="outbox.drain", cron="* * * * *", max_attempts=1)
async def drain_outbox(ctx: dict[str, Any]) -> dict[str, int]:
    """Processes a batch of pending outbound messages waiting to be delivered."""
    del ctx
    drained = await drain_once()
    return {"drained": drained}
