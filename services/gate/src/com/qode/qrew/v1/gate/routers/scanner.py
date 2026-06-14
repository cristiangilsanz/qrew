import uuid
from datetime import date as date_type
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.gate.database import get_db
from com.qode.qrew.v1.gate.services.infra.limiter import limiter
from com.qode.qrew.v1.gate.services.scanner.security import decode_scanner_token_for_refresh
from com.qode.qrew.v1.gate.repositories.scanner import ScannerRepository
from com.qode.qrew.v1.gate.schemas.scanner import ScannerTokenResponse
from com.qode.qrew.v1.gate.services.audit import AuditService
from com.qode.qrew.v1.gate.services.scanner import ScannerError, ScannerService

router = APIRouter(prefix="/scanners", tags=["scanners"])
_bearer = HTTPBearer(auto_error=True)

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Invalid scanner token", "field": None},
)


def _claims_from(
    payload: dict[str, Any],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, date_type]:
    try:
        scanner_id = uuid.UUID(str(payload["scanner_id"]))
        venue_id = uuid.UUID(str(payload["venue_id"]))
        event_id = uuid.UUID(str(payload["event_id"]))
        scan_date = date_type.fromisoformat(str(payload["date"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise _INVALID_TOKEN from exc
    if payload.get("type") != "scanner":
        raise _INVALID_TOKEN
    return scanner_id, venue_id, event_id, scan_date


@router.post(
    "/refresh",
    response_model=ScannerTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Self-service scanner JWT refresh",
)
@limiter.limit("60/hour")  # type: ignore[misc]
async def refresh_scanner(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> ScannerTokenResponse:
    del request
    try:
        payload = decode_scanner_token_for_refresh(credentials.credentials)
    except InvalidTokenError as exc:
        raise _INVALID_TOKEN from exc
    scanner_id, venue_id, event_id, scan_date = _claims_from(payload)
    service = ScannerService(ScannerRepository(db), AuditService())
    try:
        scanner, token = await service.refresh_self(scanner_id, venue_id, event_id, scan_date)
    except ScannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    return ScannerTokenResponse(
        scanner_id=scanner.id,
        token=token,
        expires_in_hours=service.token_ttl_hours,
    )
