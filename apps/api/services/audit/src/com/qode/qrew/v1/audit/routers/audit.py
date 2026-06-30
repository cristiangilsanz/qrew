from fastapi import APIRouter, Depends, status

from com.qode.qrew.v1.audit.core.dependencies import get_chain_verifier, verify_internal_api_key
from com.qode.qrew.v1.audit.schemas.verify import AuditVerifyResponse
from com.qode.qrew.v1.audit.services.verifier import AuditChainVerifier

router = APIRouter(
    prefix="/audit/chain",
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get(
    "/verify",
    response_model=AuditVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify the integrity of the audit hash chain",
)
async def verify_chain(
    verifier: AuditChainVerifier = Depends(get_chain_verifier),
) -> AuditVerifyResponse:
    result = await verifier.verify()
    return AuditVerifyResponse(
        valid=result.valid,
        event_count=result.event_count,
        tampered_ids=result.tampered_ids,
    )
