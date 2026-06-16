from fastapi import APIRouter, Depends, status

from com.qode.qrew.v1.audit.core.dependencies import verify_internal_api_key
from com.qode.qrew.v1.audit.schemas.verify import AuditVerifyResponse
from com.qode.qrew.v1.audit.services import AuditChainVerifier

router = APIRouter(
    prefix="/v1/admin/audit",
    dependencies=[Depends(verify_internal_api_key)],
)


def _verifier() -> AuditChainVerifier:
    return AuditChainVerifier()


@router.get(
    "/chain/verify",
    response_model=AuditVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify the integrity of the audit hash chain",
)
async def audit_chain_verify(
    verifier: AuditChainVerifier = Depends(_verifier),
) -> AuditVerifyResponse:
    result = await verifier.verify()
    return AuditVerifyResponse(
        valid=result.valid,
        event_count=result.event_count,
        tampered_ids=result.tampered_ids,
    )
