# paginates the outbox rows stuck in the dead letter queue
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.utils.pagination import cursor_paginate
from com.qode.qrew.v1.identity.models.outbox import OutboxEvent, dlq_query


# returns a page of outbox rows parked in the dead letter queue
async def paginate_dlq(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[OutboxEvent], str | None]:
    return await cursor_paginate(
        db,
        dlq_query(),
        sort_column=OutboxEvent.created_at,
        id_column=OutboxEvent.id,
        limit=limit,
        cursor=cursor,
    )
