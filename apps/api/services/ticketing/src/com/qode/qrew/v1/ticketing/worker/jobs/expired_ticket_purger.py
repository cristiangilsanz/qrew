# deletes expired tickets on a periodic schedule
from typing import Any, cast

import structlog
from jobs import job, parse_crontab
from sqlalchemy import text

from com.qode.qrew.v1.ticketing.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)

_DELETE_EXPIRED = text("DELETE FROM ticketing.tickets WHERE state = 'expired'")


# deletes every expired ticket and returns how many were removed
async def purge_expired() -> int:
    async with AsyncSessionLocal() as session, session.begin():
        raw = await session.execute(_DELETE_EXPIRED)
        deleted = cast(int, raw.rowcount)  # type: ignore[union-attr]
    await logger.ainfo("tickets.purge_expired", deleted=deleted)
    return deleted


# deletes expired tickets on a nightly schedule
@job("tickets.purge_expired", cron=parse_crontab("30 4 * * *"), max_attempts=1)
async def run_purge_expired(ctx: dict[str, Any]) -> None:
    del ctx
    await purge_expired()
