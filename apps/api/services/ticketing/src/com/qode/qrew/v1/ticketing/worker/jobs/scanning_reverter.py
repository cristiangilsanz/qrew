# returns a ticket whose shown qr was never scanned back to its issued state
from typing import Any, cast

import structlog
from sqlalchemy import text

from jobs import job, parse_crontab
from com.qode.qrew.v1.ticketing.core.config import settings
from com.qode.qrew.v1.ticketing.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)

# a shown qr outlives its token by a margin so a scan in flight is never undone
_GRACE_SECONDS = 60

_REVERT_STALE_SCANNING = text(
    """
    UPDATE ticketing.tickets
    SET state = 'issued', state_updated_at = now(), updated_at = now()
    WHERE state = 'scanning'
      AND state_updated_at < now() - make_interval(secs => :stale_after)
    """
)


# moves every abandoned scanning ticket back so its owner can show the qr again
async def revert_stale_scanning() -> int:
    stale_after = settings.ticket_qr_ttl_seconds + _GRACE_SECONDS
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(_REVERT_STALE_SCANNING, {"stale_after": stale_after})
        reverted = cast(int, result.rowcount)  # type: ignore[union-attr]
    if reverted:
        await logger.ainfo("tickets.scanning_reverted", reverted=reverted)
    return reverted


# reverts abandoned scanning tickets on a periodic schedule
@job("tickets.revert_stale_scanning", cron=parse_crontab("* * * * *"), max_attempts=1)
async def run_revert_stale_scanning(ctx: dict[str, Any]) -> None:
    del ctx
    await revert_stale_scanning()
