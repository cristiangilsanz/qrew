from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.services.auth.security import verify_password
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.auth.logout import BLACKLIST_JTI_PREFIX
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class AccountDeletionError(DomainError):
    """Raised when an account deletion cannot be completed."""


class AccountDeletionService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        passkey_repo: PasskeyCredentialRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._user_repo = user_repo
        self._session_repo = session_repo
        self._passkey_repo = passkey_repo
        self._redis = redis
        self._audit = audit

    async def delete(self, user: User, current_password: str) -> None:
        """Verifies the current password then permanently removes all user data and active sessions."""
        if user.deleted_at is not None:
            raise AccountDeletionError("Account is already deleted")

        if not verify_password(current_password, user.hashed_password):
            raise AccountDeletionError("Current password is incorrect", field="current_password")

        self._anonymise(user)
        await self._user_repo.save(user)

        await self._passkey_repo.delete_all_by_user_id(user.id)

        jtis = await self._session_repo.delete_all_by_user_id(user.id)
        ttl = settings.refresh_token_expire_days * 24 * 3600
        for jti in jtis:
            await self._redis.setex(BLACKLIST_JTI_PREFIX + jti, ttl, "revoked")

        await logger.ainfo("account_deleted", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.ACCOUNT_DELETED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.ACCOUNT_DELETED)

    @staticmethod
    def _anonymise(user: User) -> None:
        """Overwrites all personal data with placeholder values while keeping the account record intact."""
        tombstone = str(user.id)
        user.full_name = "Deleted User"
        user.email = f"deleted-{tombstone}@deleted.local"
        user.phone_number = f"+0{tombstone.replace('-', '')[:14]}"
        user.email_verified = False
        user.phone_number_verified = False
        user.email_verification_token = None
        user.email_verification_token_expires_at = None
        user.phone_number_otp = None
        user.phone_number_otp_expires_at = None
        user.pending_email = None
        user.pending_email_verification_token = None
        user.pending_email_token_expires_at = None
        user.pending_phone_number = None
        user.pending_phone_otp = None
        user.pending_phone_otp_expires_at = None
        user.national_id_hash = None
        user.national_id_number = None
        user.kyc_status = KycStatus.not_submitted
        user.registration_ip = "0.0.0.0"  # noqa: S104
        user.device_fingerprint = None
        user.is_active = False
        user.deleted_at = datetime.now(UTC)
