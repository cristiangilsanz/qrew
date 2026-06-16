from typing import Any

import structlog
from sqlalchemy import text

from jobs import job, parse_crontab
from com.qode.qrew.v1.catalog.core.database import AsyncSessionLocal
from com.qode.qrew.v1.catalog.repositories.search.tsvector import update_all_sql, update_one_sql
from com.qode.qrew.v1.catalog.repositories.search.events import EVENTS_SEARCH_CONFIG

logger = structlog.get_logger(__name__)


@job("search.reindex_event")
async def reindex_event(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Recompute the search vector for one event row on demand."""
    del ctx
    row_id = payload["event_id"]
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(text(update_one_sql(EVENTS_SEARCH_CONFIG)), {"row_id": row_id})


@job("search.reindex_events", cron=parse_crontab("0 5 * * *"), max_attempts=1)
async def reindex_events(ctx: dict[str, Any]) -> dict[str, Any]:
    """Recompute the search vector for every event row."""
    del ctx
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(text(update_all_sql(EVENTS_SEARCH_CONFIG)))
    updated = int(getattr(result, "rowcount", 0) or 0)
    await logger.ainfo("search_reindex_completed", updated=updated)
    return {"reindexed": updated}
