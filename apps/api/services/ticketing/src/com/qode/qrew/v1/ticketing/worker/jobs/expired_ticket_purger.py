# deletes expired tickets on a periodic schedule
from typing import cast

import structlog
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
