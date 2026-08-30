# tests the second factor a login challenge accepts
import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyotp
import pytest

from com.qode.qrew.v1.identity.services.application.authentication.login.guards.totp import (
    TotpError,
    TotpService,
    _hash_backup,
)


# builds a totp service whose repository and audit trail are stand ins
def _make_service() -> tuple[TotpService, MagicMock]:
    repo = MagicMock()
    repo.save = AsyncMock()
    audit = MagicMock()
    audit.record = AsyncMock()
    return TotpService(repo, audit), repo


# builds a user with the second factor in the state under test
def _user(*, enabled: bool = True, secret: str | None = None, backups: list[str] | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        totp_enabled=enabled,
        totp_secret=secret,
        totp_backup_codes_json=json.dumps([_hash_backup(c) for c in backups]) if backups else None,
    )


class TestGenerateSetup:
    # verifies that enrolment hands back a secret a uri and its backup codes
    def test_returns_a_secret_a_uri_and_backup_codes(self) -> None:
        service, _ = _make_service()
        secret, uri, backups = service.generate_setup(_user(enabled=False))  # type: ignore[arg-type]
        assert secret
        assert uri.startswith("otpauth://totp/")
        assert len(backups) == len(set(backups))


class TestConfirm:
    # verifies that a wrong first code leaves the factor switched off
    async def test_refuses_a_wrong_first_code(self) -> None:
        service, repo = _make_service()
        secret = pyotp.random_base32()
        with pytest.raises(TotpError, match="rejected"):
            await service.confirm(_user(enabled=False), secret, "000000", [])  # type: ignore[arg-type]
        repo.save.assert_not_awaited()

    # verifies that a correct first code stores the secret and its backups
    async def test_enables_the_factor_on_a_correct_code(self) -> None:
        service, repo = _make_service()
        secret = pyotp.random_base32()
        user = _user(enabled=False)
        await service.confirm(user, secret, pyotp.TOTP(secret).now(), ["abcd1234"])  # type: ignore[arg-type]
        assert user.totp_enabled is True
        assert user.totp_secret == secret
        assert json.loads(user.totp_backup_codes_json) != ["abcd1234"]
        repo.save.assert_awaited_once()


class TestVerifyLogin:
    # verifies that an account without the factor cannot be challenged
    async def test_refuses_when_the_factor_is_not_enabled(self) -> None:
        service, _ = _make_service()
        with pytest.raises(TotpError, match="not enabled"):
            await service.verify_login(_user(enabled=False), "000000")  # type: ignore[arg-type]

    # verifies that the current code passes
    async def test_accepts_the_current_code(self) -> None:
        service, _ = _make_service()
        secret = pyotp.random_base32()
        await service.verify_login(_user(secret=secret), pyotp.TOTP(secret).now())  # type: ignore[arg-type]

    # verifies that a backup code passes once and is then spent
    async def test_accepts_a_backup_code_once(self) -> None:
        service, repo = _make_service()
        user = _user(secret=pyotp.random_base32(), backups=["abcd1234"])
        await service.verify_login(user, "abcd1234")  # type: ignore[arg-type]
        assert json.loads(user.totp_backup_codes_json) == []
        repo.save.assert_awaited_once()

    # verifies that a code matching neither the clock nor a backup is refused
    async def test_refuses_an_unknown_code(self) -> None:
        service, _ = _make_service()
        user = _user(secret=pyotp.random_base32(), backups=["abcd1234"])
        with pytest.raises(TotpError, match="rejected"):
            await service.verify_login(user, "zzzzzzzz")  # type: ignore[arg-type]


class TestDisable:
    # verifies that an account without the factor cannot switch it off
    async def test_refuses_when_the_factor_is_not_enabled(self) -> None:
        service, _ = _make_service()
        with pytest.raises(TotpError, match="not enabled"):
            await service.disable(_user(enabled=False), "000000")  # type: ignore[arg-type]

    # verifies that a correct code switches the factor off
    async def test_switches_the_factor_off(self) -> None:
        service, repo = _make_service()
        secret = pyotp.random_base32()
        user = _user(secret=secret)
        await service.disable(user, pyotp.TOTP(secret).now())  # type: ignore[arg-type]
        assert user.totp_enabled is False
        repo.save.assert_awaited_once()
