# authenticates a user by password and issues a session setup or totp challenge
import uuid
from typing import NoReturn

import structlog

from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    create_totp_token,
    extract_jti,
    hash_password,
    verify_password,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from observability import traced
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.session import Session
from com.qode.qrew.v1.identity.models.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.repositories.device import DeviceRepository
from com.qode.qrew.v1.identity.repositories.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.authentication.auth import LoginRequest, LoginResponse
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.breach_check import (
    PasswordBreachChecker,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.anomaly import (
    LoginAnomalyService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.lockout import (
    LoginLockoutService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.session_cap import (
    SessionCapEnforcer,
)

logger = structlog.get_logger(__name__)

_DUMMY_HASH = hash_password("dummy-timing-pad")
_INVALID_CREDENTIALS = "Invalid email or password"


class LoginError(DomainError):
    pass


class LoginService:
    # stores the repositories and guards the login flow uses
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

    # authenticates a user and issues whichever token their state calls for
    @traced("auth.login")
    async def login(
        self,
        request: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
        device_id: uuid.UUID | None = None,
    ) -> LoginResponse:
        user = await self._repo.get_by_email(request.email)
        if user is None:
            await self._handle_unknown_email(request.password)

        await self._check_not_locked(user.id)
        await self._verify_credentials(user, request.password, ip_address)
        await self._reset_lockout(user.id)
        password_compromised = await self._check_breach(user.id, request.password, ip_address)

        self._ensure_email_verified(user)
        self._ensure_account_active(user)

        if await self._is_setup_complete(user):
            if user.totp_enabled:
                return self._issue_totp_challenge(user, password_compromised)
            return await self._issue_full_session(
                user,
                ip_address,
                user_agent,
                device_fingerprint,
                device_id,
                password_compromised,
            )
        return await self._issue_setup_token(user, password_compromised)

    # verifies against a dummy hash to hide that no account matched the email
    async def _handle_unknown_email(self, password: str) -> NoReturn:
        verify_password(password, _DUMMY_HASH)
        await logger.awarning("login_failed", reason="invalid_credentials")
        await self._audit_safe(AuditAction.LOGIN_FAILED, payload={"reason": "invalid_credentials"})
        raise LoginError(_INVALID_CREDENTIALS)

    # rejects a login attempt against a locked account
    async def _check_not_locked(self, user_id: uuid.UUID) -> None:
        if self._lockout is not None:
            await self._lockout.check_not_locked(user_id)

    # verifies the password and records a lockout worthy failure
    async def _verify_credentials(self, user: User, password: str, ip_address: str | None) -> None:
        if verify_password(password, user.hashed_password):
            return
        await logger.awarning("login_failed", reason="invalid_credentials", user_id=str(user.id))
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

    # clears the account's failed attempt count after a successful login
    async def _reset_lockout(self, user_id: uuid.UUID) -> None:
        if self._lockout is not None:
            await self._lockout.reset(user_id)

    # checks whether the password appears in a known breach
    async def _check_breach(
        self, user_id: uuid.UUID, password: str, ip_address: str | None
    ) -> bool:
        if self._breach_checker is None:
            return False
        return await self._breach_checker.is_compromised(user_id, password, ip_address)

    # rejects a login whose email is not yet verified
    def _ensure_email_verified(self, user: User) -> None:
        if user.email_verified:
            return
        raise LoginError(_INVALID_CREDENTIALS)

    # rejects a login against an inactive account
    def _ensure_account_active(self, user: User) -> None:
        if user.is_active:
            return
        raise LoginError(_INVALID_CREDENTIALS)

    # checks whether a user has finished every onboarding step
    async def _is_setup_complete(self, user: User) -> bool:
        return (
            user.phone_number_verified
            and user.kyc_status != KycStatus.not_submitted
            and await self._passkey_repo.has_passkey(user.id)
        )

    # binds the device persists the session and issues a full access token
    async def _issue_full_session(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
        device_id: uuid.UUID | None,
        password_compromised: bool,
    ) -> LoginResponse:
        bound_device_id = await self.resolve_bound_device(user.id, device_id)
        refresh_token = create_refresh_token(str(user.id))
        session_jti = extract_jti(refresh_token)
        access_token = create_access_token(
            str(user.id),
            device_id=str(bound_device_id) if bound_device_id else None,
            session_jti=session_jti,
            is_admin=user.is_admin,
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

    # issues a token that requires a totp code before a full session is granted
    def _issue_totp_challenge(self, user: User, password_compromised: bool) -> LoginResponse:
        return LoginResponse(
            access_token=create_totp_token(str(user.id)),
            totp_required=True,
            password_compromised=password_compromised,
        )

    # issues a token that lets the user finish the remaining onboarding steps
    async def _issue_setup_token(self, user: User, password_compromised: bool) -> LoginResponse:
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

    # runs the anomaly check without letting a failure interrupt the login
    async def _run_anomaly_check(
        self,
        user: User,
        ip_address: str | None,
        device_fingerprint: str | None,
    ) -> None:
        if self._anomaly is None:
            return
        try:
            await self._anomaly.check(user, ip_address, device_fingerprint)
        except Exception as exc:
            await logger.awarning("anomaly_check_error", user_id=str(user.id), error=repr(exc))

    # evicts the oldest sessions once the user exceeds the session cap
    async def _enforce_session_cap(self, user_id: uuid.UUID) -> None:
        if self._session_cap is None:
            return
        await self._session_cap.enforce(user_id)

    # writes the new session tied to its refresh token
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

    # resolves the caller's device if it is bound and not revoked
    async def resolve_bound_device(
        self, user_id: uuid.UUID, device_id: uuid.UUID | None
    ) -> uuid.UUID | None:
        if device_id is None or self._device_repo is None:
            return None
        device = await self._device_repo.get_by_id(device_id)
        if device is None or device.user_id != user_id or device.revoked_at is not None:
            return None
        return device.id

    # records an audit event without letting a failure interrupt the login
    async def _audit_safe(self, action: AuditAction, **kwargs: object) -> None:
        try:
            await self._audit.record(action=action, **kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))
