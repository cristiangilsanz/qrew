import uuid
from datetime import datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.core.database import get_db
from com.qode.qrew.v1.entry.core.dependencies import (
    get_current_user,
    get_redis,
    get_scanner,
    limiter,
    require_event_member,
)
from com.qode.qrew.v1.entry.core.errors import EventNotFoundError, NotEventMemberError
from com.qode.qrew.v1.entry.core.utils.jwt import decode_scanner_token
from com.qode.qrew.v1.entry.models.projections import User
from com.qode.qrew.v1.entry.models.scanner import Scanner
from com.qode.qrew.v1.entry.schemas.entry.entry import (
    EntryValidateRequest,
    EntryValidateResponse,
)
from com.qode.qrew.v1.entry.schemas.entry.entry_stats import EntryStatsResponse
from com.qode.qrew.v1.entry.services.application.audit import AuditService
from com.qode.qrew.v1.entry.services.application.entry.entry import validate_entry
from com.qode.qrew.v1.entry.services.application.entry.entry_stats import (
    compute_entry_stats,
)

entry_router = APIRouter(prefix="/entry", tags=["entry"])
events_router = APIRouter(prefix="/events", tags=["entry"])
_bearer = HTTPBearer(auto_error=True)


def _audit_service() -> AuditService:
    return AuditService()


def _claims_or_401(token: str) -> tuple[uuid.UUID | None, uuid.UUID]:
    try:
        payload = decode_scanner_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid scanner token", "field": None},
        ) from exc
    venue_raw = payload.get("venue_id")
    event_raw = payload.get("event_id")
    if not isinstance(venue_raw, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Scanner token missing venue_id", "field": None},
        )
    try:
        venue_id = uuid.UUID(venue_raw)
        event_id = uuid.UUID(event_raw) if isinstance(event_raw, str) else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Scanner token has invalid scoping", "field": None},
        ) from exc
    return event_id, venue_id


@entry_router.post(
    "/validate",
    response_model=EntryValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a ticket QR at the gate",
)
@limiter.limit("600/minute")  # type: ignore[misc]
async def validate_entry_endpoint(
    request: Request,
    body: EntryValidateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    scanner: Scanner = Depends(get_scanner),
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
    audit: AuditService = Depends(_audit_service),
) -> EntryValidateResponse:
    del request
    event_id, venue_id = _claims_or_401(credentials.credentials)
    outcome = await validate_entry(
        db,
        redis,
        ticket_jwt=body.ticket_jwt,
        scanner=scanner,
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=audit,
    )
    return EntryValidateResponse(
        allowed=outcome.allowed,
        reason=outcome.reason.value if outcome.reason else None,
        ticket_id=outcome.ticket_id,
        holder_user_id=outcome.holder_user_id,
        scanned_at=outcome.scanned_at,
    )


# ---------------------------------------------------------------------------
# Entry statistics
# ---------------------------------------------------------------------------


@events_router.get(
    "/{event_id}/entry-stats",
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
    del request
    try:
        await require_event_member(db, event_id, current_user.id)
    except EventNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        ) from None
    except NotEventMemberError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Not a member of this organisation", "field": None},
        ) from None
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
