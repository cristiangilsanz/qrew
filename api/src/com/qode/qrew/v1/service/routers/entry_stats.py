import uuid
from datetime import datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.infra.redis import get_redis
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.repositories.event import EventRepository
from com.qode.qrew.v1.service.repositories.organisation import (
    OrganisationMemberRepository,
)
from com.qode.qrew.v1.service.schemas.entry_stats import EntryStatsResponse
from com.qode.qrew.v1.service.services.entry_stats import compute_entry_stats

router = APIRouter(tags=["entry-stats"])


async def _require_event_member(
    db: AsyncSession, event_id: uuid.UUID, user: User
) -> None:
    """Gate the caller on membership of the organisation that owns this event."""
    event = await EventRepository(db).get_by_id(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )
    member = await OrganisationMemberRepository(db).get(event.organisation_id, user.id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Not a member of this organisation",
                "field": None,
            },
        )


@router.get(
    "/events/{event_id}/entry-stats",
    response_model=EntryStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Per-event entry rollup for the organiser console",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_entry_stats(
    request: Request,
    event_id: uuid.UUID,
    since: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> EntryStatsResponse:
    """Return a cached entry rollup over a settable since window."""
    del request
    await _require_event_member(db, event_id, current_user)
    stats = await compute_entry_stats(db, redis, event_id=event_id, since=since)
    return EntryStatsResponse(
        event_id=stats.event_id,
        since=stats.since,
        total_issued=stats.total_issued,
        total_entered=stats.total_entered,
        total_remaining=stats.total_remaining,
        rejections_by_reason=stats.rejections_by_reason,
        last_scan_at=stats.last_scan_at,
    )
