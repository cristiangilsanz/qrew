from typing import Any

from sqlalchemy import Select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from pagination.cursor import decode_cursor, encode_cursor


async def cursor_paginate(
    session: AsyncSession,
    stmt: Select[Any],
    sort_column: InstrumentedAttribute[Any],
    id_column: InstrumentedAttribute[Any],
    limit: int,
    cursor: str | None,
) -> tuple[list[Any], str | None]:
    """Execute a keyset-paginated query and return results with a continuation token."""
    ordered = stmt.order_by(sort_column.desc(), id_column.desc())
    if cursor is not None:
        sort_value, last_id = decode_cursor(cursor)
        ordered = ordered.where(
            or_(
                sort_column < sort_value,
                and_(sort_column == sort_value, id_column < last_id),
            )
        )
    result = await session.execute(ordered.limit(limit + 1))
    rows = list(result.scalars().all())
    if len(rows) <= limit:
        return rows, None
    visible = rows[:limit]
    last = visible[-1]
    next_cursor = encode_cursor(
        getattr(last, sort_column.key), str(getattr(last, id_column.key))
    )
    return visible, next_cursor
