import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.api import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.identity.core.auth.auth import get_admin_user
from com.qode.qrew.v1.identity.core.infra.database import get_db
from com.qode.qrew.v1.identity.core.infra.limiter import limiter
from com.qode.qrew.v1.identity.core.outbox.model import OutboxEvent
from com.qode.qrew.v1.identity.models.auth.user import User

router = APIRouter(prefix="/outbox", tags=["admin-outbox"])


class OutboxDlqItem(BaseModel):
    id: uuid.UUID
    aggregate_type: str
    aggregate_id: str
    job_name: str
    attempt_count: int
    last_error: str | None
    dlq_reason: str | None
    created_at: datetime
    dispatched_at: datetime | None


@router.get(
    "/dlq",
    response_model=Page[OutboxDlqItem],
    status_code=status.HTTP_200_OK,
    summary="Paginate outbox rows the drainer parked in the DLQ",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def list_dlq(
    request: Request,
    cursor: str | None = None,
    limit: int = 20,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Page[OutboxDlqItem]:
    """Return outbox rows that were parked in the DLQ."""
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = select(OutboxEvent).where(OutboxEvent.dlq_reason.is_not(None))
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=OutboxEvent.created_at,
        id_column=OutboxEvent.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[OutboxDlqItem](
        items=[
            OutboxDlqItem(
                id=row.id,
                aggregate_type=row.aggregate_type,
                aggregate_id=row.aggregate_id,
                job_name=row.job_name,
                attempt_count=row.attempt_count,
                last_error=row.last_error,
                dlq_reason=row.dlq_reason,
                created_at=row.created_at,
                dispatched_at=row.dispatched_at,
            )
            for row in rows
        ],
        next_cursor=next_cursor,
    )
