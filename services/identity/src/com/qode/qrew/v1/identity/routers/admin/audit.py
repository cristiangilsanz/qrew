from fastapi import APIRouter, Depends, Request, status

from com.qode.qrew.v1.identity.core.auth.auth import get_admin_user
from com.qode.qrew.v1.identity.core.infra.limiter import limiter
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.schemas.admin.admin import AuditVerifyResponse
from com.qode.qrew.v1.identity.services.audit import AuditChainVerifier

router = APIRouter()


@router.get(
    "/audit/verify",
    response_model=AuditVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify the integrity of the audit hash chain",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def audit_verify(
    request: Request,
    _admin: User = Depends(get_admin_user),
) -> AuditVerifyResponse:
    """Verify the audit chain integrity."""
    result = await AuditChainVerifier().verify()
    return AuditVerifyResponse(
        valid=result.valid,
        event_count=result.event_count,
        tampered_ids=result.tampered_ids,
    )
