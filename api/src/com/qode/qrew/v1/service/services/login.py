import uuid

import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    extract_jti,
    hash_password,
    verify_password,
)
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.session import Session
from com.qode.qrew.v1.service.models.user import KycStatus
from com.qode.qrew.v1.service.repositories.device import DeviceRepository
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.repositories.session import SessionRepository
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import LoginRequest, LoginResponse
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.login_anomaly import LoginAnomalyService

logger = structlog.get_logger(__name__)

_DUMMY_HASH = hash_password("dummy-timing-pad")


class LoginError(DomainError):
    """A business-rule violation raised when a login attempt cannot be completed."""


class LoginService:
    def __init__(
        self,
        repo: UserRepository,
        passkey_repo: PasskeyCredentialRepository,
        audit: AuditService,
        session_repo: SessionRepository | None = None,
        anomaly: LoginAnomalyService | None = None,
        device_repo: DeviceRepository | None = None,
    ) -> None:
        self._repo = repo
        self._passkey_repo = passkey_repo
        self._audit = audit
        self._session_repo = session_repo
        self._anomaly = anomaly
        self._device_repo = device_repo

    async def login(
        self,
        request: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
        device_id: uuid.UUID | None = None,
    ) -> LoginResponse:
        """Authenticate a user, returning a setup or full-access token."""
        user = await self._repo.get_by_email(request.email)

        if user is None:
            verify_password(request.password, _DUMMY_HASH)
            await logger.awarning("login_failed", reason="invalid_credentials")
            try:
                await self._audit.record(
                    action=AuditAction.LOGIN_FAILED,
                    payload={"reason": "invalid_credentials"},
                )
            except Exception:
                await logger.awarning(
                    "audit_write_failed", action=AuditAction.LOGIN_FAILED
                )
            raise LoginError("Invalid email or password")

        if not verify_password(request.password, user.hashed_password):
            await logger.awarning(
                "login_failed",
                reason="invalid_credentials",
                user_id=str(user.id),
            )
            try:
                await self._audit.record(
                    action=AuditAction.LOGIN_FAILED,
                    actor_id=user.id,
                    entity_type="user",
                    entity_id=str(user.id),
                    payload={"reason": "invalid_credentials"},
                )
            except Exception:
                await logger.awarning(
                    "audit_write_failed", action=AuditAction.LOGIN_FAILED
                )
            raise LoginError("Invalid email or password")

        if not user.email_verified:
            await logger.awarning(
                "login_failed",
                reason="email_not_verified",
                user_id=str(user.id),
            )
            raise LoginError("Please verify your email before logging in")

        if not user.is_active:
            await logger.awarning(
                "login_failed",
                reason="account_deactivated",
                user_id=str(user.id),
            )
            raise LoginError("Account has been deactivated")

        setup_complete = (
            user.phone_number_verified
            and user.kyc_status != KycStatus.not_submitted
            and await self._passkey_repo.has_passkey(user.id)
        )

        if setup_complete:
            bound_device_id = await self.resolve_bound_device(user.id, device_id)
            refresh_token = create_refresh_token(str(user.id))
            session_jti = extract_jti(refresh_token)
            access_token = create_access_token(
                str(user.id),
                device_id=str(bound_device_id) if bound_device_id else None,
                session_jti=session_jti,
            )
            await self._persist_session(
                user.id,
                refresh_token,
                ip_address,
                user_agent,
                device_fingerprint,
                bound_device_id,
            )
            await logger.ainfo("user_logged_in", user_id=str(user.id))
            try:
                await self._audit.record(
                    action=AuditAction.LOGIN,
                    actor_id=user.id,
                    entity_type="user",
                    entity_id=str(user.id),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_fingerprint_hash=device_fingerprint,
                    payload={"setup_complete": True},
                )
            except Exception:
                await logger.awarning("audit_write_failed", action=AuditAction.LOGIN)
            if self._anomaly is not None:
                try:
                    await self._anomaly.check(user, ip_address, device_fingerprint)
                except Exception:
                    await logger.awarning("anomaly_check_error", user_id=str(user.id))
            return LoginResponse(access_token=access_token, refresh_token=refresh_token)

        await logger.ainfo("user_logged_in_setup_required", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.LOGIN,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                payload={"setup_complete": False},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.LOGIN)
        return LoginResponse(
            access_token=create_setup_token(str(user.id)),
            setup_required=True,
        )

    async def _persist_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
        device_id: uuid.UUID | None = None,
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
                device_id=device_id,
            )
        )

    async def resolve_bound_device(
        self, user_id: uuid.UUID, device_id: uuid.UUID | None
    ) -> uuid.UUID | None:
        """Return device_id if it belongs to the user and is not revoked."""
        if device_id is None or self._device_repo is None:
            return None
        device = await self._device_repo.get_by_id(device_id)
        if device is None or device.user_id != user_id or device.revoked_at is not None:
            return None
        return device.id
