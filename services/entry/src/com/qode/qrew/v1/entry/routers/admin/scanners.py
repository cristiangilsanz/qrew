import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.core.database import get_db
from com.qode.qrew.v1.entry.core.dependencies import limiter
from com.qode.qrew.v1.entry.models.identity import User
from com.qode.qrew.v1.entry.repositories.scanner import ScannerRepository
from com.qode.qrew.v1.entry.routers.auth import get_admin_user
from com.qode.qrew.v1.entry.schemas.scanner import (
    ScannerCreateRequest,
    ScannerDeactivateResponse,
    ScannerListResponse,
    ScannerRotateRequest,
    ScannerSummaryResponse,
    ScannerTokenResponse,
)
from com.qode.qrew.v1.entry.services.audit import AuditService
from com.qode.qrew.v1.entry.services.scanner import ScannerError, ScannerService

router = APIRouter(prefix="/admin")


def _get_scanner_service(db: AsyncSession = Depends(get_db)) -> ScannerService:
    return ScannerService(ScannerRepository(db), AuditService())


def _scanner_summary(scanner: object) -> ScannerSummaryResponse:
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
    service: ScannerService = Depends(_get_scanner_service),
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
    service: ScannerService = Depends(_get_scanner_service),
) -> ScannerListResponse:
    del request
    scanners = await service.list_all()
    return ScannerListResponse(scanners=[_scanner_summary(s) for s in scanners])


@router.get(
    "/scanners/{scanner_id}",
    response_model=ScannerSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a single scanner",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_scanner_by_id(
    request: Request,
    scanner_id: uuid.UUID,
    _admin: User = Depends(get_admin_user),
    service: ScannerService = Depends(_get_scanner_service),
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
    service: ScannerService = Depends(_get_scanner_service),
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
    service: ScannerService = Depends(_get_scanner_service),
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
