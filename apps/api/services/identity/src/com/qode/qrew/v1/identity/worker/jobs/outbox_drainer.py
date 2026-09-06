# drains the outbox on a periodic schedule
from typing import Any

from jobs import job, parse_crontab
from com.qode.qrew.v1.identity.services.application.outbox import drain_once


# drains a batch of the outbox
@job("outbox.drain", cron=parse_crontab("* * * * *"), max_attempts=1)
async def drain_outbox(ctx: dict[str, Any]) -> dict[str, int]:
    del ctx
    drained = await drain_once()
    return {"drained": drained}
