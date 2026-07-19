import structlog
from sqlalchemy import text

from com.qode.qrew.v1.ticketing.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)

_DELETE_EXPIRED = text("DELETE FROM ticketing.tickets WHERE state = 'expired'")


async def purge_expired() -> int:
    """Hard-deletes tickets in the expired state, keeping the tickets list clean."""
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(_DELETE_EXPIRED)
        deleted = result.rowcount
    await logger.ainfo("tickets.purge_expired", deleted=deleted)
    return deleted
