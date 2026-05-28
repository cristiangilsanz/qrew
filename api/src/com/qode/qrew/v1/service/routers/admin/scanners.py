import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from com.qode.qrew.v1.service.core.auth.auth import get_admin_user
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.schemas.scanner.scanner import (
    ScannerCreateRequest,
    ScannerDeactivateResponse,
    ScannerListResponse,
    ScannerRotateRequest,
    ScannerSummaryResponse,
    ScannerTokenResponse,
)
from com.qode.qrew.v1.service.services.scanner.scanner import (
    ScannerError,
    ScannerService,
)

from ._deps import get_scanner_service

router = APIRouter()


def _scanner_summary(scanner: object) -> ScannerSummaryResponse:
    """Adapt a scanner row to its admin response shape."""
    return ScannerSummaryResponse.model_validate(scanner, from_attributes=True)


@router.post(
    "/scanners",
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
    """Register a scanner and return its initial credential."""
    scanner, token = await service.create(
        admin.id, body.name, body.venue_id, body.event_id, body.date
    )
    return ScannerTokenResponse(
        scanner_id=scanner.id,
        token=token,
        expires_in_hours=service.token_ttl_hours,
    )


@router.get(
    "/scanners",
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
    """List every scanner record."""
    scanners = await service.list_all()
    return ScannerListResponse(scanners=[_scanner_summary(s) for s in scanners])


@router.post(
    "/scanners/{scanner_id}/rotate",
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
    """Mint a fresh credential for an existing scanner."""
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


@router.delete(
    "/scanners/{scanner_id}",
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
    """Deactivate a scanner."""
    try:
        await service.deactivate(admin.id, scanner_id)
    except ScannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    return ScannerDeactivateResponse(message="Scanner deactivated.")
