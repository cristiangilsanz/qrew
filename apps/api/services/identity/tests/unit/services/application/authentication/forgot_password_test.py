# tests that a password reset only goes through for a token that matches the stored hash
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.services.application.authentication.account.changes.forgot_password import (  # noqa: E501
    ForgotPasswordError,
    ForgotPasswordService,
)

_MODULE = (
    "com.qode.qrew.v1.identity.services.application.authentication.account.changes.forgot_password"
)

TOKEN = "a-reset-token"


# builds a user holding the hash of a reset token, the way the column stores it
def _user(*, token: str | None = TOKEN, expired: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        is_active=True,
        hashed_password="old-hash",
        password_reset_token=None if token is None else pii_crypto.hash_lookup(token),
        password_reset_token_expires_at=datetime.now(UTC) + timedelta(hours=-1 if expired else 1),
    )


# builds the service over a repository that looks a token up by its hash
def _make_service(found: object) -> tuple[ForgotPasswordService, MagicMock]:
    repo = MagicMock()
    repo.get_by_password_reset_token = AsyncMock(return_value=found)
    repo.save = AsyncMock()
    notifier = MagicMock()
    notifier.send_forgot_password = AsyncMock()
    return ForgotPasswordService(repo, notifier), repo


class TestResetPassword:
    # verifies that the token the user was emailed actually resets the password
    async def test_accepts_the_token_that_was_emailed(self) -> None:
        user = _user()
        service, repo = _make_service(user)
        with patch(f"{_MODULE}.hash_password", return_value="new-hash"):
            await service.reset_password(TOKEN, "Password1!")
        assert user.hashed_password == "new-hash"
        assert user.password_reset_token is None
        assert user.password_reset_token_expires_at is None
        repo.save.assert_awaited()

    # verifies that the lookup keys off the token's hash, never off the token itself
    async def test_looks_the_token_up_by_its_own_value(self) -> None:
        service, repo = _make_service(_user())
        with patch(f"{_MODULE}.hash_password", return_value="new-hash"):
            await service.reset_password(TOKEN, "Password1!")
        repo.get_by_password_reset_token.assert_awaited_once_with(TOKEN)

    # verifies that an unknown token is refused
    async def test_refuses_an_unknown_token(self) -> None:
        service, _ = _make_service(None)
        with pytest.raises(ForgotPasswordError, match="expired"):
            await service.reset_password(TOKEN, "Password1!")

    # verifies that a row carrying somebody else's hash is refused
    async def test_refuses_a_row_whose_hash_does_not_match(self) -> None:
        service, _ = _make_service(_user(token="another-token"))
        with pytest.raises(ForgotPasswordError, match="expired"):
            await service.reset_password(TOKEN, "Password1!")

    # verifies that a row with no reset pending is refused
    async def test_refuses_a_row_with_no_token_stored(self) -> None:
        service, _ = _make_service(_user(token=None))
        with pytest.raises(ForgotPasswordError, match="expired"):
            await service.reset_password(TOKEN, "Password1!")

    # verifies that an expired token is refused
    async def test_refuses_an_expired_token(self) -> None:
        service, _ = _make_service(_user(expired=True))
        with pytest.raises(ForgotPasswordError, match="expired"):
            await service.reset_password(TOKEN, "Password1!")


class TestRequestReset:
    # verifies that the column keeps the hash of the token and never the token
    async def test_stores_only_the_hash_of_the_token(self) -> None:
        user = _user(token=None)
        repo = MagicMock()
        repo.get_by_email = AsyncMock(return_value=user)
        repo.save = AsyncMock()
        notifier = MagicMock()
        notifier.send_forgot_password = AsyncMock()
        service = ForgotPasswordService(repo, notifier)
        with (
            patch(f"{_MODULE}.generate_token", return_value=TOKEN),
            patch(f"{_MODULE}.settings", SimpleNamespace(email_verification_token_expire_hours=1)),
        ):
            await service.request_reset("user@example.com")
        assert user.password_reset_token == pii_crypto.hash_lookup(TOKEN)
        assert user.password_reset_token != TOKEN
        notifier.send_forgot_password.assert_awaited_once_with(user.email, user.full_name, TOKEN)
