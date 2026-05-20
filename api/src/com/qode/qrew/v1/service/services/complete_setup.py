import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import (
    create_access_token,
    create_refresh_token,
)
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import LoginResponse
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)


class SetupError(DomainError):
    """Raised when setup cannot be completed because a required step is missing."""


class CompleteSetupService:
    def __init__(
        self,
        user_repo: UserRepository,
        passkey_repo: PasskeyCredentialRepository,
        audit: AuditService,
    ) -> None:
        self._user_repo = user_repo
        self._passkey_repo = passkey_repo
        self._audit = audit

    async def complete(self, user: User) -> LoginResponse:
        """Issue full tokens once all onboarding steps are complete."""
        if not user.phone_number_verified:
            await logger.awarning(
                "setup_incomplete", reason="phone_not_verified", user_id=str(user.id)
            )
            raise SetupError("Phone number is not verified", field="phone_number")

        if user.kyc_status == KycStatus.not_submitted:
            await logger.awarning(
                "setup_incomplete", reason="kyc_not_submitted", user_id=str(user.id)
            )
            raise SetupError("KYC document has not been submitted", field="kyc")

        if not await self._passkey_repo.has_passkey(user.id):
            await logger.awarning(
                "setup_incomplete",
                reason="passkey_not_registered",
                user_id=str(user.id),
            )
            raise SetupError("Passkey has not been registered", field="passkey")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        await logger.ainfo("setup_completed", user_id=str(user.id))

        try:
            await self._audit.record(
                action=AuditAction.SETUP_COMPLETED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.SETUP_COMPLETED
            )

        return LoginResponse(access_token=access_token, refresh_token=refresh_token)
