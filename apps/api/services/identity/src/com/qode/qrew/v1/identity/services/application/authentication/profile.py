import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.audit import AuditEvent
from com.qode.qrew.v1.identity.models.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.audit import AuditRepository
from com.qode.qrew.v1.identity.repositories.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.authentication.auth import OnboardingStatusResponse
from com.qode.qrew.v1.identity.core.utils.pagination import cursor_paginate


class ProfileService:
    """Read-only queries that back the user metadata endpoints."""

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
        if not email_verified:
            current_step = "email"
        elif not phone_verified:
            current_step = "phone"
        elif not kyc_submitted:
            current_step = "kyc"
        elif not has_passkey:
            current_step = "passkey"
        else:
            current_step = "pending"
        return OnboardingStatusResponse(
            email_verified=email_verified,
            phone_verified=phone_verified,
            kyc_submitted=kyc_submitted,
            passkey_registered=has_passkey,
            is_complete=is_complete,
            current_step=current_step,
        )

    async def paginate_audit(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        action: str | None = None,
        since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[AuditEvent], str | None]:
        """Return a cursor-paginated page of audit events for the given user."""
        stmt = self._audit_repo.query_for_user(user_id, action=action, since=since)
        return await cursor_paginate(
            db,
            stmt,
            sort_column=AuditEvent.created_at,
            id_column=AuditEvent.id,
            limit=limit,
            cursor=cursor,
        )
