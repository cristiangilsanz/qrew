import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    hash_password,
    verify_password,
)
from com.qode.qrew.v1.service.models.user import KycStatus
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import LoginRequest, LoginResponse

logger = structlog.get_logger(__name__)

_DUMMY_HASH = hash_password("dummy-timing-pad")


class LoginError(DomainError):
    """A business-rule violation raised when a login attempt cannot be completed."""


class LoginService:
    def __init__(
        self, repo: UserRepository, passkey_repo: PasskeyCredentialRepository
    ) -> None:
        self._repo = repo
        self._passkey_repo = passkey_repo

    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate a user, returning a setup or full-access token."""
        user = await self._repo.get_by_email(request.email)

        if user is None:
            verify_password(request.password, _DUMMY_HASH)
            await logger.awarning("login_failed", reason="invalid_credentials")
            raise LoginError("Invalid email or password")

        if not verify_password(request.password, user.hashed_password):
            await logger.awarning(
                "login_failed",
                reason="invalid_credentials",
                user_id=str(user.id),
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
            access_token = create_access_token(str(user.id))
            refresh_token = create_refresh_token(str(user.id))
            await logger.ainfo("user_logged_in", user_id=str(user.id))
            return LoginResponse(access_token=access_token, refresh_token=refresh_token)

        await logger.ainfo("user_logged_in_setup_required", user_id=str(user.id))
        return LoginResponse(
            access_token=create_setup_token(str(user.id)),
            setup_required=True,
        )
