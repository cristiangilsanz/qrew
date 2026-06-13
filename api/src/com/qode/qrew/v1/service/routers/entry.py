import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import get_scanner
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.infra.redis import get_redis
from com.qode.qrew.v1.service.core.scanner.security import decode_scanner_token
from com.qode.qrew.v1.service.models.scanner.scanner import Scanner
from com.qode.qrew.v1.service.schemas.entry import (
    EntryValidateRequest,
    EntryValidateResponse,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.entry import validate_entry

router = APIRouter(prefix="/entry", tags=["entry"])
_bearer = HTTPBearer(auto_error=True)


def _claims_or_401(token: str) -> tuple[uuid.UUID | None, uuid.UUID]:
    """Return (event_id, venue_id) from the scanner JWT; raise 401 on malformed."""
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


@router.post(
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
) -> EntryValidateResponse:
    """Verify the ticket JWT, defeat relays, and atomically finalise entry."""
    del request
    event_id, venue_id = _claims_or_401(credentials.credentials)
    outcome = await validate_entry(
        db,
        redis,
        ticket_jwt=body.ticket_jwt,
        scanner=scanner,
        scanner_event_id=event_id,
        scanner_venue_id=venue_id,
        audit=AuditService(),
    )
    return EntryValidateResponse(
        allowed=outcome.allowed,
        reason=outcome.reason.value if outcome.reason else None,
        ticket_id=outcome.ticket_id,
        holder_user_id=outcome.holder_user_id,
        scanned_at=outcome.scanned_at,
    )
