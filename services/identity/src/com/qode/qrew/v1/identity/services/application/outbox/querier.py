from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.utils.pagination import cursor_paginate
from com.qode.qrew.v1.identity.models.outbox import OutboxEvent, dlq_query


async def paginate_dlq(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[OutboxEvent], str | None]:
    """Return a cursor-paginated page of DLQ outbox rows."""
    return await cursor_paginate(
        db,
        dlq_query(),
        sort_column=OutboxEvent.created_at,
        id_column=OutboxEvent.id,
        limit=limit,
        cursor=cursor,
    )
