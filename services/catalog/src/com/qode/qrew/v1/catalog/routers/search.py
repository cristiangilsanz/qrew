import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.routers import Page, clamp_limit
from com.qode.qrew.v1.catalog.database import get_db
from com.qode.qrew.v1.catalog.services.infra.limiter import limiter
from com.qode.qrew.v1.catalog.repositories.search import build_search_clause, encode_next_cursor
from com.qode.qrew.v1.catalog.schemas.search import EventSearchResult
from com.qode.qrew.v1.catalog.repositories.search.events import EVENTS_SEARCH_CONFIG
from com.qode.qrew.v1.catalog.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "",
    response_model=Page[EventSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Public catalog list of events with cursor pagination and search",
)
@router.get(
    "/search",
    response_model=Page[EventSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search published events by text and filters",
    include_in_schema=False,
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def search_events(
    request: Request,
    q: str | None = Query(default=None, max_length=256),
    city: str | None = Query(default=None, max_length=128),
    category: str | None = Query(default=None, max_length=64),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
    cursor: str | None = None,
    limit: int = Query(default=settings.search_default_limit, ge=1),
    db: AsyncSession = Depends(get_db),
) -> Page[EventSearchResult]:
    del request
    page_limit = clamp_limit(limit, default=settings.search_default_limit)
    page_limit = min(page_limit, settings.search_max_limit)

    clause = build_search_clause(
        config=EVENTS_SEARCH_CONFIG,
        q=q,
        filters={"category": category, "venue_city": city},
        cursor=cursor,
    )

    select_fragments = ["id", "name", "organiser_name", "venue_city", "starts_at"]
    if clause.rank_expression is not None:
        select_fragments.append(
            f"{clause.rank_expression} AS {EVENTS_SEARCH_CONFIG.rank_column_alias}"
        )

    where_fragments = list(clause.where_fragments)
    if from_ is not None:
        clause.parameters["from_ts"] = from_
        where_fragments.append("starts_at >= :from_ts")
    if to is not None:
        clause.parameters["to_ts"] = to
        where_fragments.append("starts_at <= :to_ts")

    where_clause = " AND ".join(where_fragments) if where_fragments else "TRUE"
    statement = (
        f"SELECT {', '.join(select_fragments)} "
        f"FROM {EVENTS_SEARCH_CONFIG.table} "
        f"WHERE {where_clause} "
        f"ORDER BY {clause.order_by} "
        f"LIMIT :search_limit"
    )
    sql = text(statement)
    clause.parameters["search_limit"] = page_limit + 1

    result = await db.execute(sql, clause.parameters)
    rows = list(result.mappings())

    next_cursor: str | None = None
    if len(rows) > page_limit:
        last = rows[page_limit - 1]
        rank_value = last.get(EVENTS_SEARCH_CONFIG.rank_column_alias)
        rows = rows[:page_limit]
        if rank_value is not None:
            next_cursor = encode_next_cursor(float(rank_value), str(last["id"]))

    items = [
        EventSearchResult(
            id=uuid.UUID(str(row["id"])),
            name=row["name"],
            organiser_name=row.get("organiser_name"),
            venue_city=row.get("venue_city"),
            starts_at=row.get("starts_at"),
            rank=(
                float(row[EVENTS_SEARCH_CONFIG.rank_column_alias])
                if EVENTS_SEARCH_CONFIG.rank_column_alias in row
                else None
            ),
        )
        for row in rows
    ]
    await logger.ainfo(
        "events.search.indexed",
        result_count=len(items),
        has_query=q is not None,
        page_limit=page_limit,
    )
    return Page[EventSearchResult](items=items, next_cursor=next_cursor)
