"""Tests for HIBP breach check at login."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import KycStatus
from com.qode.qrew.v1.service.schemas.auth.auth import LoginRequest
from com.qode.qrew.v1.service.services.auth import breach_check as breach_check_mod
from com.qode.qrew.v1.service.services.auth import login as login_mod
from com.qode.qrew.v1.service.services.auth.breach_check import PasswordBreachChecker
from com.qode.qrew.v1.service.services.auth.login import LoginError, LoginService


def _user(setup_complete: bool = True) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "alice@example.com"
    u.email_verified = True
    u.is_active = True
    u.phone_number_verified = setup_complete
    u.kyc_status = KycStatus.approved if setup_complete else KycStatus.not_submitted
    u.hashed_password = "hash"
    return u


def _build_service(passkey_present: bool = True) -> tuple[LoginService, AsyncMock]:
    user = _user()
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    passkey_repo = AsyncMock()
    passkey_repo.has_passkey = AsyncMock(return_value=passkey_present)
    audit = AsyncMock()
    audit.record = AsyncMock()
    breach_checker = PasswordBreachChecker(audit)
    svc = LoginService(repo, passkey_repo, audit, breach_checker=breach_checker)
    return svc, audit


def _patch_password(mp: pytest.MonkeyPatch, ok: bool = True) -> None:
    def _verify(_p: str, _h: str) -> bool:
        return ok

    mp.setattr(login_mod, "verify_password", _verify)


def _patch_hibp(
    mp: pytest.MonkeyPatch,
    *,
    compromised: bool = False,
    raises: bool = False,
) -> None:
    async def _hibp(_password: str) -> bool:
        if raises:
            error_msg = "HIBP down"
            raise RuntimeError(error_msg)
        return compromised

    mp.setattr(breach_check_mod, "is_password_pwned", _hibp)


async def test_login_sets_password_compromised_when_pwned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, audit = _build_service()
    _patch_password(monkeypatch, ok=True)
    _patch_hibp(monkeypatch, compromised=True)

    result = await svc.login(LoginRequest(email="a@b.com", password="x"))

    assert result.password_compromised is True
    actions = [call.kwargs.get("action") for call in audit.record.await_args_list]
    assert AuditAction.LOGIN_COMPROMISED_PASSWORD in actions


async def test_login_clean_password_keeps_flag_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, audit = _build_service()
    _patch_password(monkeypatch, ok=True)
    _patch_hibp(monkeypatch, compromised=False)

    result = await svc.login(LoginRequest(email="a@b.com", password="x"))

    assert result.password_compromised is False
    actions = [call.kwargs.get("action") for call in audit.record.await_args_list]
    assert AuditAction.LOGIN_COMPROMISED_PASSWORD not in actions


async def test_login_swallows_hibp_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A HIBP outage must NOT prevent login or set the flag."""
    svc, _ = _build_service()
    _patch_password(monkeypatch, ok=True)
    _patch_hibp(monkeypatch, raises=True)

    result = await svc.login(LoginRequest(email="a@b.com", password="x"))

    assert result.password_compromised is False
    assert result.access_token


async def test_setup_required_response_also_carries_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compromised flag must propagate to the setup-token response too."""
    user = _user(setup_complete=False)
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    passkey_repo = AsyncMock()
    passkey_repo.has_passkey = AsyncMock(return_value=False)
    audit = AsyncMock()
    breach_checker = PasswordBreachChecker(audit)
    svc = LoginService(repo, passkey_repo, audit, breach_checker=breach_checker)

    _patch_password(monkeypatch, ok=True)
    _patch_hibp(monkeypatch, compromised=True)

    result = await svc.login(LoginRequest(email="a@b.com", password="x"))

    assert result.setup_required is True
    assert result.password_compromised is True


async def test_hibp_not_called_when_password_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HIBP check should never run on a failed credential — would waste an API call."""
    svc, _ = _build_service()
    _patch_password(monkeypatch, ok=False)

    called = False

    async def _hibp(_password: str) -> bool:
        nonlocal called
        called = True
        return False

    monkeypatch.setattr(breach_check_mod, "is_password_pwned", _hibp)

    with pytest.raises(LoginError):
        await svc.login(LoginRequest(email="a@b.com", password="x"))

    assert called is False
