import contextlib
import uuid

from fastapi import APIRouter, Depends, Request, status

from com.qode.qrew.v1.identity.core.api import Page
from com.qode.qrew.v1.identity.core.auth.auth import get_current_user
from com.qode.qrew.v1.identity.core.infra.limiter import limiter
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.schemas.device.device import (
    DeviceAttestRequest,
    DeviceAttestResponse,
    DeviceBindBeginResponse,
    DeviceBindCompleteRequest,
    DeviceBindCompleteResponse,
    DeviceResponse,
    DeviceRevokeAllResponse,
    DeviceRevokeResponse,
    FingerprintReportRequest,
    FingerprintReportResponse,
)
from com.qode.qrew.v1.identity.services.device.device import DeviceError, DeviceService
from com.qode.qrew.v1.identity.services.device.device_attestation import (
    DeviceAttestationError,
    DeviceAttestationService,
)
from com.qode.qrew.v1.identity.services.device.device_binding import (
    DeviceBindingError,
    DeviceBindingService,
)
from com.qode.qrew.v1.identity.services.device.fingerprint import FingerprintService

from ._deps import (
    domain_error,
    get_device_attestation_service,
    get_device_binding_service,
    get_device_service,
    get_fingerprint_service,
)

router = APIRouter()


@router.post(
    "/devices/fingerprint",
    response_model=FingerprintReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Report a device fingerprint for the current user",
)
@limiter.limit("30/hour")  # type: ignore[misc]
async def report_fingerprint(
    request: Request,
    body: FingerprintReportRequest,
    current_user: User = Depends(get_current_user),
    service: FingerprintService = Depends(get_fingerprint_service),
) -> FingerprintReportResponse:
    """Report a device fingerprint for the current user."""
    flagged = await service.report(
        current_user,
        body.fingerprint_hash,
        body.user_agent,
        body.ip_address,
    )
    return FingerprintReportResponse(message="Fingerprint recorded.", flagged=flagged)


@router.post(
    "/devices/bind/begin",
    response_model=DeviceBindBeginResponse,
    status_code=status.HTTP_200_OK,
    summary="Begin device binding",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def device_bind_begin(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: DeviceBindingService = Depends(get_device_binding_service),
) -> DeviceBindBeginResponse:
    """Begin device binding."""
    challenge = await service.begin(current_user)
    return DeviceBindBeginResponse(challenge=challenge)


@router.post(
    "/devices/bind/complete",
    response_model=DeviceBindCompleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete device binding",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def device_bind_complete(
    request: Request,
    body: DeviceBindCompleteRequest,
    current_user: User = Depends(get_current_user),
    service: DeviceBindingService = Depends(get_device_binding_service),
) -> DeviceBindCompleteResponse:
    """Complete device binding."""
    try:
        device = await service.complete(current_user, body.name, body.public_key, body.signature)
        return DeviceBindCompleteResponse(
            device_id=str(device.id),
            message="Device bound successfully.",
        )
    except DeviceBindingError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/devices/attest",
    response_model=DeviceAttestResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a device integrity attestation",
)
@limiter.limit("10/hour")  # type: ignore[misc]
async def device_attest(
    request: Request,
    body: DeviceAttestRequest,
    current_user: User = Depends(get_current_user),
    service: DeviceAttestationService = Depends(get_device_attestation_service),
) -> DeviceAttestResponse:
    """Submit a device integrity attestation."""
    try:
        result = await service.attest(current_user.id, body.platform, body.token)
        return DeviceAttestResponse(
            message="Device attested successfully.",
            platform=result.platform,
        )
    except DeviceAttestationError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_403_FORBIDDEN) from exc


@router.get(
    "/devices",
    response_model=Page[DeviceResponse],
    status_code=status.HTTP_200_OK,
    summary="List the current user's bound devices",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def list_devices(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: DeviceService = Depends(get_device_service),
) -> Page[DeviceResponse]:
    """List the current user's bound devices."""
    devices = await service.list_devices(current_user)
    items = [
        DeviceResponse(
            id=d.id,
            name=d.name,
            created_at=d.created_at,
            last_seen_at=d.last_seen_at,
        )
        for d in devices
    ]
    return Page[DeviceResponse](items=items, next_cursor=None)


@router.post(
    "/devices/{device_id}/revoke",
    response_model=DeviceRevokeResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a specific bound device",
)
@limiter.limit("20/hour")  # type: ignore[misc]
async def revoke_device(
    request: Request,
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DeviceService = Depends(get_device_service),
) -> DeviceRevokeResponse:
    """Revoke a specific bound device."""
    calling_device_header = request.headers.get("X-Calling-Device-Id")
    calling_device_id: uuid.UUID | None = None
    if calling_device_header:
        with contextlib.suppress(ValueError):
            calling_device_id = uuid.UUID(calling_device_header)
    try:
        await service.revoke_device(current_user, device_id, calling_device_id)
        return DeviceRevokeResponse(message="Device revoked successfully.")
    except DeviceError as exc:
        raise domain_error(exc.message, exc.field, status.HTTP_400_BAD_REQUEST) from exc


@router.post(
    "/devices/revoke-all",
    response_model=DeviceRevokeAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke every device except the caller",
)
@limiter.limit("5/hour")  # type: ignore[misc]
async def revoke_all_devices(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: DeviceService = Depends(get_device_service),
) -> DeviceRevokeAllResponse:
    """Revoke every other device and kill all sessions."""
    calling_device_header = request.headers.get("X-Calling-Device-Id")
    calling_device_id: uuid.UUID | None = None
    if calling_device_header:
        with contextlib.suppress(ValueError):
            calling_device_id = uuid.UUID(calling_device_header)
    revoked_count = await service.revoke_all_devices(current_user, calling_device_id)
    return DeviceRevokeAllResponse(
        message=f"Revoked {revoked_count} device(s).",
        revoked_count=revoked_count,
    )
