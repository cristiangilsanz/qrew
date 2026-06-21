from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.identity.models.user import KycStatus
from com.qode.qrew.v1.identity.services.application.authentication.login.flow.login import (
    LoginError,
    LoginService,
)
from com.qode.qrew.v1.identity.services.application.authentication.login.guards.lockout import (
    LoginLockoutError,
)
from com.qode.qrew.v1.identity.schemas.authentication.auth import LoginRequest
from conftest import make_user

_MOD = "com.qode.qrew.v1.identity.services.application.authentication.login.flow.login"
_PATCH_VERIFY = f"{_MOD}.verify_password"


def _make_request(*, email: str = "user@example.com", password: str = "Pass1234!") -> LoginRequest:
    return LoginRequest(email=email, password=password)


def _make_svc(
    *,
    user: object = None,
    has_passkey: bool = True,
) -> LoginService:
    repo = MagicMock()
    repo.get_by_email = AsyncMock(return_value=user)

    passkey_repo = MagicMock()
    passkey_repo.has_passkey = AsyncMock(return_value=has_passkey)

    audit = AsyncMock()
    audit.record = AsyncMock()

    session_repo = MagicMock()
    session_repo.create = AsyncMock()
    session_repo.count_by_user_id = AsyncMock(return_value=1)
    session_repo.get_oldest_by_user_id = AsyncMock(return_value=[])
    session_repo.delete_by_jti = AsyncMock()

    svc = LoginService(
        repo=repo,
        passkey_repo=passkey_repo,
        audit=audit,
        session_repo=session_repo,
    )
    return svc


class TestLoginUnknownEmail:
    async def test_raises_for_unknown_email(self) -> None:
        svc = _make_svc(user=None)
        with (
            patch(_PATCH_VERIFY, return_value=False),
            pytest.raises(LoginError, match="Invalid email or password"),
        ):
            await svc.login(_make_request())


class TestLoginWrongPassword:
    async def test_raises_for_wrong_password(self) -> None:
        user = make_user()
        svc = _make_svc(user=user)
        with (
            patch(_PATCH_VERIFY, return_value=False),
            pytest.raises(LoginError, match="Invalid email or password"),
        ):
            await svc.login(_make_request())

    async def test_records_failure_with_lockout(self) -> None:
        user = make_user()
        lockout = MagicMock()
        lockout.check_not_locked = AsyncMock()
        lockout.record_failure = AsyncMock()
        lockout.reset = AsyncMock()

        svc = _make_svc(user=user)
        svc._lockout = lockout

        with (
            patch(_PATCH_VERIFY, return_value=False),
            pytest.raises(LoginError),
        ):
            await svc.login(_make_request())
        lockout.record_failure.assert_awaited_once()


class TestLoginLockout:
    async def test_raises_lockout_error_when_locked(self) -> None:
        user = make_user()
        lockout = MagicMock()
        lockout.check_not_locked = AsyncMock(
            side_effect=LoginLockoutError("Locked", retry_after_seconds=120)
        )
        svc = _make_svc(user=user)
        svc._lockout = lockout
        with (
            patch(_PATCH_VERIFY, return_value=True),
            pytest.raises(LoginLockoutError),
        ):
            await svc.login(_make_request())


class TestLoginEmailNotVerified:
    async def test_raises_for_unverified_email(self) -> None:
        user = make_user(email_verified=False)
        svc = _make_svc(user=user)
        with (
            patch(_PATCH_VERIFY, return_value=True),
            pytest.raises(LoginError, match="Invalid email or password"),
        ):
            await svc.login(_make_request())


class TestLoginInactiveAccount:
    async def test_raises_for_inactive_account(self) -> None:
        user = make_user(is_active=False)
        svc = _make_svc(user=user)
        with (
            patch(_PATCH_VERIFY, return_value=True),
            pytest.raises(LoginError, match="Invalid email or password"),
        ):
            await svc.login(_make_request())


class TestLoginSetupIncomplete:
    async def test_returns_setup_token_when_phone_not_verified(self) -> None:
        user = make_user(phone_number_verified=False)
        svc = _make_svc(user=user)
        with patch(_PATCH_VERIFY, return_value=True):
            response = await svc.login(_make_request())
        assert response.setup_required is True
        assert response.refresh_token is None

    async def test_returns_setup_token_when_kyc_not_submitted(self) -> None:
        user = make_user(kyc_status=KycStatus.not_submitted)
        svc = _make_svc(user=user, has_passkey=True)
        with patch(_PATCH_VERIFY, return_value=True):
            response = await svc.login(_make_request())
        assert response.setup_required is True

    async def test_returns_setup_token_when_no_passkey(self) -> None:
        user = make_user()
        svc = _make_svc(user=user, has_passkey=False)
        with patch(_PATCH_VERIFY, return_value=True):
            response = await svc.login(_make_request())
        assert response.setup_required is True


class TestLoginSetupComplete:
    async def test_returns_full_session_tokens(self) -> None:
        user = make_user()
        svc = _make_svc(user=user, has_passkey=True)
        with patch(_PATCH_VERIFY, return_value=True):
            response = await svc.login(_make_request())
        assert response.setup_required is False
        assert response.access_token
        assert response.refresh_token

    async def test_password_compromised_flag_propagates(self) -> None:
        user = make_user()
        breach_checker = MagicMock()
        breach_checker.is_compromised = AsyncMock(return_value=True)
        svc = _make_svc(user=user, has_passkey=True)
        svc._breach_checker = breach_checker
        with patch(_PATCH_VERIFY, return_value=True):
            response = await svc.login(_make_request())
        assert response.password_compromised is True

    async def test_audit_failure_does_not_break_login(self) -> None:
        user = make_user()
        svc = _make_svc(user=user, has_passkey=True)
        svc._audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch(_PATCH_VERIFY, return_value=True):
            response = await svc.login(_make_request())
        assert response.access_token
