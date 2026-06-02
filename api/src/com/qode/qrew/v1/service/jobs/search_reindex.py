from typing import Any

import structlog
from sqlalchemy import inspect, text

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.core.jobs import job
from com.qode.qrew.v1.service.core.search import update_all_sql, update_one_sql
from com.qode.qrew.v1.service.search.events import EVENTS_SEARCH_CONFIG

logger = structlog.get_logger(__name__)


async def _events_table_exists() -> bool:
    async with AsyncSessionLocal() as session:
        raw = await session.connection()

        def _has(connection: object) -> bool:
            inspector = inspect(connection)
            if inspector is None:
                return False
            return EVENTS_SEARCH_CONFIG.table in inspector.get_table_names()

        return await raw.run_sync(_has)


@job(name="search.reindex_events", cron="0 5 * * *", max_attempts=1)
async def reindex_events(ctx: dict[str, Any]) -> dict[str, Any]:
    """Recompute the search vector for every event row."""
    del ctx
    if not await _events_table_exists():
        await logger.ainfo("search_reindex_skipped", reason="events_table_missing")
        return {"reindexed": 0, "skipped": True}
    async with AsyncSessionLocal() as session, session.begin():
        result = await session.execute(text(update_all_sql(EVENTS_SEARCH_CONFIG)))
    updated = int(getattr(result, "rowcount", 0) or 0)
    await logger.ainfo("search_reindex_completed", updated=updated)
    return {"reindexed": updated, "skipped": False}


@job(name="search.reindex_event", max_attempts=3)
async def reindex_event(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """Recompute the search vector for one event row on demand."""
    del ctx
    if not await _events_table_exists():
        return
    row_id = payload["event_id"]
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            text(update_one_sql(EVENTS_SEARCH_CONFIG)), {"row_id": row_id}
        )
