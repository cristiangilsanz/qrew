from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from com.qode.qrew.v1.audit.services import AuditChainVerifier
from com.qode.qrew.v1.audit.settings import settings

router = APIRouter(prefix="/v1/admin/audit")


class AuditVerifyResponse(BaseModel):
    valid: bool
    event_count: int
    tampered_ids: list[str]


@router.get(
    "/chain/verify",
    response_model=AuditVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify the integrity of the audit hash chain",
)
async def audit_chain_verify(
    x_internal_key: str = Header(alias="X-Internal-Key"),
) -> AuditVerifyResponse:
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await AuditChainVerifier().verify()
    return AuditVerifyResponse(
        valid=result.valid,
        event_count=result.event_count,
        tampered_ids=result.tampered_ids,
    )
