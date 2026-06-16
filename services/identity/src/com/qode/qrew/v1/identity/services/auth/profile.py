import uuid
from datetime import datetime

from sqlalchemy import Select

from com.qode.qrew.v1.identity.models.audit.audit import AuditEvent
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.audit.audit import AuditRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.auth.auth import OnboardingStatusResponse


class ProfileService:
    """Read-only queries that back the /me profile endpoints."""

    def __init__(
        self,
        passkey_repo: PasskeyCredentialRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._passkey_repo = passkey_repo
        self._audit_repo = audit_repo

    async def get_onboarding_status(self, user: User) -> OnboardingStatusResponse:
        """Return which onboarding steps the user has completed."""
        has_passkey = await self._passkey_repo.has_passkey(user.id)
        kyc_submitted = user.kyc_status != KycStatus.not_submitted
        email_verified = user.email_verified
        phone_verified = user.phone_number_verified
        is_complete = email_verified and phone_verified and kyc_submitted and has_passkey
        return OnboardingStatusResponse(
            email_verified=email_verified,
            phone_verified=phone_verified,
            kyc_submitted=kyc_submitted,
            passkey_registered=has_passkey,
            is_complete=is_complete,
        )

    def query_user_audit(
        self,
        user_id: uuid.UUID,
        action: str | None = None,
        since: datetime | None = None,
    ) -> Select[tuple[AuditEvent]]:
        """Build a filtered audit query for the given user."""
        return self._audit_repo.query_for_user(user_id, action=action, since=since)
