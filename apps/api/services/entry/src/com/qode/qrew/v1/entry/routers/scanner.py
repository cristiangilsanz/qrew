import uuid
from datetime import date as date_type
from datetime import date as today_date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.core.database import get_db
from com.qode.qrew.v1.entry.core.dependencies import (
    get_admin_user,
    get_current_user,
    get_scanner_service,
    limiter,
    require_event_member,
)
from com.qode.qrew.v1.entry.core.errors import EventNotFoundError, NotEventMemberError
from com.qode.qrew.v1.entry.core.utils.jwt import decode_scanner_token_for_refresh
from com.qode.qrew.v1.entry.models.projections import User
from com.qode.qrew.v1.entry.repositories.projections import EventRepository
from com.qode.qrew.v1.entry.schemas.scanner import (
    ScannerCreateRequest,
    ScannerDeactivateResponse,
    ScannerForEventRequest,
    ScannerListResponse,
    ScannerRotateRequest,
    ScannerSummaryResponse,
    ScannerTokenResponse,
)
from com.qode.qrew.v1.entry.services.application.scanner import (
    ScannerError,
    ScannerService,
)

router = APIRouter(prefix="/scanners", tags=["scanners"])
admin_router = APIRouter(prefix="/admin/scanners", tags=["admin-scanners"])

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


def _scanner_summary(scanner: object) -> ScannerSummaryResponse:
    return ScannerSummaryResponse.model_validate(scanner, from_attributes=True)


# ---------------------------------------------------------------------------
# Scanner self-service
# ---------------------------------------------------------------------------


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
    service: ScannerService = Depends(get_scanner_service),
) -> ScannerTokenResponse:
    del request
    try:
        payload = decode_scanner_token_for_refresh(credentials.credentials)
    except InvalidTokenError as exc:
        raise _INVALID_TOKEN from exc
    scanner_id, venue_id, event_id, scan_date = _claims_from(payload)
    try:
        scanner, token = await service.refresh_self(
            scanner_id, venue_id, event_id, scan_date
        )
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


# ---------------------------------------------------------------------------
# Org-member scanner creation
# ---------------------------------------------------------------------------


@router.post(
    "/for-event/{event_id}",
    response_model=ScannerTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scanner token for an event (org members and admins)",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def create_scanner_for_event(
    request: Request,
    event_id: uuid.UUID,
    body: ScannerForEventRequest,
    current_user: User = Depends(get_current_user),
    service: ScannerService = Depends(get_scanner_service),
    db: AsyncSession = Depends(get_db),
) -> ScannerTokenResponse:
    del request
    event = await EventRepository(db).get_by_id(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )
    if not current_user.is_admin:
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
    scan_date = body.date if body.date is not None else today_date.today()
    scanner, token = await service.create(
        current_user.id, body.name, event.venue_id, event_id, scan_date
    )
    return ScannerTokenResponse(
        scanner_id=scanner.id,
        token=token,
        expires_in_hours=service.token_ttl_hours,
    )


# ---------------------------------------------------------------------------
# Admin scanner management
# ---------------------------------------------------------------------------


@admin_router.post(
    "",
    response_model=ScannerTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a scanner and return its initial credential",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def create_scanner(
    request: Request,
    body: ScannerCreateRequest,
    admin: User = Depends(get_admin_user),
    service: ScannerService = Depends(get_scanner_service),
) -> ScannerTokenResponse:
    del request
    scanner, token = await service.create(
        admin.id, body.name, body.venue_id, body.event_id, body.date
    )
    return ScannerTokenResponse(
        scanner_id=scanner.id,
        token=token,
        expires_in_hours=service.token_ttl_hours,
    )


@admin_router.get(
    "",
    response_model=ScannerListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all registered scanners",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_scanners(
    request: Request,
    _admin: User = Depends(get_admin_user),
    service: ScannerService = Depends(get_scanner_service),
) -> ScannerListResponse:
    del request
    scanners = await service.list_all()
    return ScannerListResponse(scanners=[_scanner_summary(s) for s in scanners])


@admin_router.get(
    "/{scanner_id}",
    response_model=ScannerSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a single scanner",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_scanner_by_id(
    request: Request,
    scanner_id: uuid.UUID,
    _admin: User = Depends(get_admin_user),
    service: ScannerService = Depends(get_scanner_service),
) -> ScannerSummaryResponse:
    del request
    try:
        scanner = await service.get_by_id(scanner_id)
    except ScannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    return _scanner_summary(scanner)


@admin_router.post(
    "/{scanner_id}/rotate",
    response_model=ScannerTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Mint a fresh credential for an existing scanner",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def rotate_scanner(
    request: Request,
    scanner_id: uuid.UUID,
    body: ScannerRotateRequest,
    admin: User = Depends(get_admin_user),
    service: ScannerService = Depends(get_scanner_service),
) -> ScannerTokenResponse:
    del request
    try:
        scanner, token = await service.rotate(
            admin.id, scanner_id, body.venue_id, body.event_id, body.date
        )
    except ScannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    return ScannerTokenResponse(
        scanner_id=scanner.id,
        token=token,
        expires_in_hours=service.token_ttl_hours,
    )


@admin_router.delete(
    "/{scanner_id}",
    response_model=ScannerDeactivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a scanner",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def deactivate_scanner(
    request: Request,
    scanner_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    service: ScannerService = Depends(get_scanner_service),
) -> ScannerDeactivateResponse:
    del request
    try:
        await service.deactivate(admin.id, scanner_id)
    except ScannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    return ScannerDeactivateResponse(message="Scanner deactivated.")
