import enum
import uuid
from datetime import datetime

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


class FingerprintAdminResponse(BaseModel):
    fingerprint_hash: str
    user_ids: list[str]
    account_count: int


class UserSummaryResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    kyc_status: str
    email_verified: bool
    phone_verified: bool
    is_admin: bool
    created_at: datetime
