# schedules and runs the jobs that keep the event search vector fresh
from typing import Any

import structlog
from sqlalchemy import text

from jobs import job, parse_crontab
from com.qode.qrew.v1.catalog.core.database import AsyncSessionLocal
from com.qode.qrew.v1.catalog.repositories.events.search.tsvector import (
    update_all_sql,
    update_one_sql,
)
from com.qode.qrew.v1.catalog.repositories.events.search.events import EVENTS_SEARCH_CONFIG

logger = structlog.get_logger(__name__)


# refreshes one event's search vector
@job("search.reindex_event")
async def reindex_event(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    del ctx
    row_id = payload["event_id"]
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(text(update_one_sql(EVENTS_SEARCH_CONFIG)), {"row_id": row_id})


# refreshes every event's search vector on a nightly schedule
@job("search.reindex_events", cron=parse_crontab("0 5 * * *"), max_attempts=1)
async def reindex_events(ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(text(update_all_sql(EVENTS_SEARCH_CONFIG)))
    updated = int(getattr(result, "rowcount", 0) or 0)
    await logger.ainfo("search_reindex_completed", updated=updated)
    return {"reindexed": updated}
