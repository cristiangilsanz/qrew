import uuid
from typing import NoReturn

import structlog

from com.qode.qrew.v1.service.core.auth.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    extract_jti,
    hash_password,
    verify_password,
)
from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.repositories.device.device import DeviceRepository
from com.qode.qrew.v1.service.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.service.schemas.auth.auth import LoginRequest, LoginResponse
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.auth.breach_check import PasswordBreachChecker
from com.qode.qrew.v1.service.services.auth.login_anomaly import LoginAnomalyService
from com.qode.qrew.v1.service.services.auth.login_lockout import LoginLockoutService
from com.qode.qrew.v1.service.services.auth.session_cap import SessionCapEnforcer

logger = structlog.get_logger(__name__)

_DUMMY_HASH = hash_password("dummy-timing-pad")
_INVALID_CREDENTIALS = "Invalid email or password"


class LoginError(DomainError):
    """Raised when a login attempt cannot be completed."""


class LoginService:
    """Authenticate users and mint setup or full access tokens."""

    def __init__(
        self,
        repo: UserRepository,
        passkey_repo: PasskeyCredentialRepository,
        audit: AuditService,
        session_repo: SessionRepository | None = None,
        anomaly: LoginAnomalyService | None = None,
        device_repo: DeviceRepository | None = None,
        lockout: LoginLockoutService | None = None,
        session_cap: SessionCapEnforcer | None = None,
        breach_checker: PasswordBreachChecker | None = None,
    ) -> None:
        self._repo = repo
        self._passkey_repo = passkey_repo
        self._audit = audit
        self._session_repo = session_repo
        self._anomaly = anomaly
        self._device_repo = device_repo
        self._lockout = lockout
        self._session_cap = session_cap
        self._breach_checker = breach_checker

    @traced("auth.login")
    async def login(
        self,
        request: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
        device_id: uuid.UUID | None = None,
    ) -> LoginResponse:
        """Authenticate a user and return a setup or full access token."""
        user = await self._repo.get_by_email(request.email)
        if user is None:
            await self._handle_unknown_email(request.password)

        await self._check_not_locked(user.id)
        await self._verify_credentials(user, request.password, ip_address)
        await self._reset_lockout(user.id)
        password_compromised = await self._check_breach(
            user.id, request.password, ip_address
        )

        self._ensure_email_verified(user)
        self._ensure_account_active(user)

        if await self._is_setup_complete(user):
            return await self._issue_full_session(
                user,
                ip_address,
                user_agent,
                device_fingerprint,
                device_id,
                password_compromised,
            )
        return await self._issue_setup_token(user, password_compromised)

    async def _handle_unknown_email(self, password: str) -> NoReturn:
        """Mimic a real password verify and reject the unknown account."""
        verify_password(password, _DUMMY_HASH)
        await logger.awarning("login_failed", reason="invalid_credentials")
        await self._audit_safe(
            AuditAction.LOGIN_FAILED, payload={"reason": "invalid_credentials"}
        )
        raise LoginError(_INVALID_CREDENTIALS)

    async def _check_not_locked(self, user_id: uuid.UUID) -> None:
        """Reject if the per-account lockout is active."""
        if self._lockout is not None:
            await self._lockout.check_not_locked(user_id)

    async def _verify_credentials(
        self, user: User, password: str, ip_address: str | None
    ) -> None:
        """Verify the user's password and record a failure if it does not match."""
        if verify_password(password, user.hashed_password):
            return
        await logger.awarning(
            "login_failed", reason="invalid_credentials", user_id=str(user.id)
        )
        await self._audit_safe(
            AuditAction.LOGIN_FAILED,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            payload={"reason": "invalid_credentials"},
        )
        if self._lockout is not None:
            await self._lockout.record_failure(user.id, ip_address)
        raise LoginError(_INVALID_CREDENTIALS)

    async def _reset_lockout(self, user_id: uuid.UUID) -> None:
        """Clear the per-account lockout after a successful credential check."""
        if self._lockout is not None:
            await self._lockout.reset(user_id)

    async def _check_breach(
        self, user_id: uuid.UUID, password: str, ip_address: str | None
    ) -> bool:
        """Check whether the supplied password appears in breach data."""
        if self._breach_checker is None:
            return False
        return await self._breach_checker.is_compromised(user_id, password, ip_address)

    def _ensure_email_verified(self, user: User) -> None:
        """Reject sign-in if the account's email is not verified."""
        if user.email_verified:
            return
        raise LoginError(_INVALID_CREDENTIALS)

    def _ensure_account_active(self, user: User) -> None:
        """Reject sign-in for a deactivated account."""
        if user.is_active:
            return
        raise LoginError(_INVALID_CREDENTIALS)

    async def _is_setup_complete(self, user: User) -> bool:
        """Return whether the user has finished onboarding."""
        return (
            user.phone_number_verified
            and user.kyc_status != KycStatus.not_submitted
            and await self._passkey_repo.has_passkey(user.id)
        )

    async def _issue_full_session(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
        device_id: uuid.UUID | None,
        password_compromised: bool,
    ) -> LoginResponse:
        """Mint full access and refresh tokens for a fully onboarded user."""
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
        await self._enforce_session_cap(user.id)
        await logger.ainfo("user_logged_in", user_id=str(user.id))
        await self._audit_safe(
            AuditAction.LOGIN,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint_hash=device_fingerprint,
            payload={"setup_complete": True},
        )
        await self._run_anomaly_check(user, ip_address, device_fingerprint)
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            password_compromised=password_compromised,
        )

    async def _issue_setup_token(
        self, user: User, password_compromised: bool
    ) -> LoginResponse:
        """Mint a setup token for a user that still has onboarding steps left."""
        await logger.ainfo("user_logged_in_setup_required", user_id=str(user.id))
        await self._audit_safe(
            AuditAction.LOGIN,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            payload={"setup_complete": False},
        )
        return LoginResponse(
            access_token=create_setup_token(str(user.id)),
            setup_required=True,
            password_compromised=password_compromised,
        )

    async def _run_anomaly_check(
        self,
        user: User,
        ip_address: str | None,
        device_fingerprint: str | None,
    ) -> None:
        """Run anomaly detection without letting it block the login flow."""
        if self._anomaly is None:
            return
        try:
            await self._anomaly.check(user, ip_address, device_fingerprint)
        except Exception:
            await logger.awarning("anomaly_check_error", user_id=str(user.id))

    async def _enforce_session_cap(self, user_id: uuid.UUID) -> None:
        """Delegate session-cap enforcement to the dedicated enforcer."""
        if self._session_cap is None:
            return
        await self._session_cap.enforce(user_id)

    async def _persist_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
        device_id: uuid.UUID | None = None,
    ) -> None:
        """Persist a new session row for a freshly minted refresh token."""
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
        """Resolve an optional device hint to a bound non-revoked device id."""
        if device_id is None or self._device_repo is None:
            return None
        device = await self._device_repo.get_by_id(device_id)
        if device is None or device.user_id != user_id or device.revoked_at is not None:
            return None
        return device.id

    async def _audit_safe(self, action: AuditAction, **kwargs: object) -> None:
        """Record an audit event without letting failure propagate."""
        try:
            await self._audit.record(action=action, **kwargs)  # type: ignore[arg-type]
        except Exception:
            await logger.awarning("audit_write_failed", action=action)
