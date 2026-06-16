import uuid

import structlog

from com.qode.qrew.v1.identity.services.auth.security import (
    create_access_token,
    create_refresh_token,
    extract_jti,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.models.auth.session import Session
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.auth.auth import LoginResponse
from com.qode.qrew.v1.identity.services.audit import AuditService

logger = structlog.get_logger(__name__)


class SetupError(DomainError):
    """Raised when setup cannot be completed because a required step is missing."""


class CompleteSetupService:
    def __init__(
        self,
        user_repo: UserRepository,
        passkey_repo: PasskeyCredentialRepository,
        audit: AuditService,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._passkey_repo = passkey_repo
        self._audit = audit
        self._session_repo = session_repo

    async def complete(
        self,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> LoginResponse:
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

        await self._persist_session(
            user.id, refresh_token, ip_address, user_agent, device_fingerprint
        )

        await logger.ainfo("setup_completed", user_id=str(user.id))

        try:
            await self._audit.record(
                action=AuditAction.SETUP_COMPLETED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.SETUP_COMPLETED, error=repr(exc)
            )

        return LoginResponse(access_token=access_token, refresh_token=refresh_token)

    async def _persist_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
    ) -> None:
        if self._session_repo is None:
            return
        jti = extract_jti(refresh_token)
        if jti is None:
            return
        await self._session_repo.create(
            Session(
                id=uuid.uuid4(),
                user_id=user_id,
                jti=jti,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
            )
        )
