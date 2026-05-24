import enum

from pydantic import BaseModel, Field


class KycAction(enum.StrEnum):
    approve = "approve"
    reject = "reject"


class KycReviewRequest(BaseModel):
    action: KycAction
    reason: str | None = Field(default=None, max_length=500)


class KycReviewResponse(BaseModel):
    user_id: str
    kyc_status: str
    message: str


class AuditVerifyResponse(BaseModel):
    valid: bool
    event_count: int
    tampered_ids: list[str]


class FingerprintAdminResponse(BaseModel):
    fingerprint_hash: str
    user_ids: list[str]
    account_count: int
