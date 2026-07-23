import uuid
from datetime import datetime

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pagination import Page
from com.qode.qrew.v1.catalog.repositories.events.search import (
    build_search_clause,
    encode_next_cursor,
)
from com.qode.qrew.v1.catalog.repositories.events.search.events import EVENTS_SEARCH_CONFIG
from com.qode.qrew.v1.catalog.schemas.event import EventSearchResult

logger = structlog.get_logger(__name__)


class SearchService:
    async def search_events(
        self,
        db: AsyncSession,
        *,
        q: str | None,
        city: str | None,
        cities: list[str] | None,
        category: str | None,
        from_: datetime | None,
        to: datetime | None,
        cursor: str | None,
        limit: int,
    ) -> Page[EventSearchResult]:
        # Merge single city + multi-city into one list
        all_cities: list[str] = []
        if cities:
            all_cities = [c for c in cities if c]
        elif city:
            all_cities = [city]

        clause = build_search_clause(
            config=EVENTS_SEARCH_CONFIG,
            q=q,
            filters={"category": category},
            cursor=cursor,
        )

        select_fragments = [
            "id",
            "name",
            "description",
            "image_url",
            "organiser_name",
            "venue_city",
            "starts_at",
        ]
        if clause.rank_expression is not None:
            select_fragments.append(
                f"{clause.rank_expression} AS {EVENTS_SEARCH_CONFIG.rank_column_alias}"
            )

        where_fragments = list(clause.where_fragments)
        if all_cities:
            placeholders = ", ".join(f":city_{i}" for i in range(len(all_cities)))
            where_fragments.append(f"venue_city IN ({placeholders})")
            for i, c in enumerate(all_cities):
                clause.parameters[f"city_{i}"] = c
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
        clause.parameters["search_limit"] = limit + 1

        result = await db.execute(sql, clause.parameters)
        rows = list(result.mappings())

        next_cursor: str | None = None
        if len(rows) > limit:
            last = rows[limit - 1]
            rank_value = last.get(EVENTS_SEARCH_CONFIG.rank_column_alias)
            rows = rows[:limit]
            if rank_value is not None:
                next_cursor = encode_next_cursor(float(rank_value), str(last["id"]))

        items = [
            EventSearchResult(
                id=uuid.UUID(str(row["id"])),
                name=row["name"],
                description=row.get("description"),
                image_url=row.get("image_url"),
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
            page_limit=limit,
        )
        return Page[EventSearchResult](items=items, next_cursor=next_cursor)
