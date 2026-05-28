"""Tests for POST /v1/auth/account/delete."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import KycStatus, User
from com.qode.qrew.v1.service.routers.auth import get_account_deletion_service
from com.qode.qrew.v1.service.services.account import account_deletion as deletion_mod
from com.qode.qrew.v1.service.services.account.account_deletion import (
    AccountDeletionError,
    AccountDeletionService,
)
from com.qode.qrew.v1.service.services.auth.logout import BLACKLIST_JTI_PREFIX

_ENDPOINT = "/v1/auth/account/delete"
_PAYLOAD: dict[str, object] = {"current_password": "Str0ng!P@ssw0rd"}


def _ok_verify(_password: str, _hashed: str) -> bool:
    return True


def _bad_verify(_password: str, _hashed: str) -> bool:
    return False


def _mock_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_admin = False
    return u


@pytest.fixture
def mock_service() -> AsyncMock:
    s = AsyncMock()
    s.delete = AsyncMock()
    return s


@pytest.fixture(autouse=True)
def override(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_account_deletion_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


async def test_delete_returns_200(client: AsyncClient, mock_service: AsyncMock) -> None:
    response = await client.post(_ENDPOINT, json=_PAYLOAD)
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()
    mock_service.delete.assert_awaited_once()


async def test_delete_returns_400_on_wrong_password(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.delete.side_effect = AccountDeletionError(
        "Current password is incorrect", field="current_password"
    )
    response = await client.post(_ENDPOINT, json=_PAYLOAD)
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "current_password"


async def test_delete_rejects_missing_password(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={})
    assert response.status_code == 422


def _build_user() -> User:
    user = User()
    user.id = uuid.uuid4()
    user.full_name = "Alice Smith"
    user.email = "alice@example.com"
    user.phone_number = "+34600111222"
    user.hashed_password = "hash"
    user.email_verified = True
    user.phone_number_verified = True
    user.email_verification_token = "tok"
    user.email_verification_token_expires_at = None
    user.phone_number_otp = "123456"
    user.phone_number_otp_expires_at = None
    user.pending_email = None
    user.pending_email_verification_token = None
    user.pending_email_token_expires_at = None
    user.pending_phone_number = None
    user.pending_phone_otp = None
    user.pending_phone_otp_expires_at = None
    user.national_id_hash = "deadbeef" * 8
    user.national_id_number = "encrypted-blob"
    user.kyc_status = KycStatus.approved
    user.registration_ip = "1.2.3.4"
    user.device_fingerprint = "fp"
    user.is_active = True
    user.is_admin = False
    user.deleted_at = None
    return user


def _build_service() -> tuple[
    AccountDeletionService, AsyncMock, AsyncMock, AsyncMock, AsyncMock
]:
    user_repo = AsyncMock()
    user_repo.save = AsyncMock()
    passkey_repo = AsyncMock()
    passkey_repo.delete_all_by_user_id = AsyncMock()
    session_repo = AsyncMock()
    session_repo.delete_all_by_user_id = AsyncMock(return_value=["jti-1", "jti-2"])
    redis = AsyncMock()
    redis.setex = AsyncMock()
    audit = AsyncMock()
    audit.record = AsyncMock()
    svc = AccountDeletionService(user_repo, session_repo, passkey_repo, redis, audit)
    return svc, user_repo, session_repo, redis, audit


async def test_service_rejects_wrong_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _, _, _, _ = _build_service()
    monkeypatch.setattr(deletion_mod, "verify_password", _bad_verify)
    with pytest.raises(AccountDeletionError, match="Current password is incorrect"):
        await svc.delete(_build_user(), "wrong")


async def test_service_rejects_double_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _, _, _, _ = _build_service()
    monkeypatch.setattr(deletion_mod, "verify_password", _ok_verify)
    user = _build_user()
    user.deleted_at = datetime.now(UTC)
    with pytest.raises(AccountDeletionError, match="already deleted"):
        await svc.delete(user, "x")


async def test_service_anonymises_pii(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, user_repo, _, _, _ = _build_service()
    monkeypatch.setattr(deletion_mod, "verify_password", _ok_verify)
    user = _build_user()
    original_id = user.id

    await svc.delete(user, "x")

    assert user.full_name == "Deleted User"
    assert user.email.startswith("deleted-")
    assert user.email.endswith("@deleted.local")
    assert user.phone_number.startswith("+0")
    assert user.email_verification_token is None
    assert user.phone_number_otp is None
    assert user.national_id_hash is None
    assert user.national_id_number is None
    assert user.kyc_status == KycStatus.not_submitted
    assert user.registration_ip == "0.0.0.0"
    assert user.device_fingerprint is None
    assert user.is_active is False
    assert user.deleted_at is not None
    assert user.id == original_id
    user_repo.save.assert_awaited_once_with(user)


async def test_service_kills_sessions_and_blacklists_jtis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _, session_repo, redis, _ = _build_service()
    monkeypatch.setattr(deletion_mod, "verify_password", _ok_verify)
    user = _build_user()

    await svc.delete(user, "x")

    session_repo.delete_all_by_user_id.assert_awaited_once_with(user.id)
    assert redis.setex.await_count == 2
    keys = [call.args[0] for call in redis.setex.await_args_list]
    assert BLACKLIST_JTI_PREFIX + "jti-1" in keys
    assert BLACKLIST_JTI_PREFIX + "jti-2" in keys


async def test_service_deletes_all_passkeys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    passkey_repo = AsyncMock()
    passkey_repo.delete_all_by_user_id = AsyncMock()
    svc = AccountDeletionService(
        AsyncMock(),
        AsyncMock(delete_all_by_user_id=AsyncMock(return_value=[])),
        passkey_repo,
        AsyncMock(),
        AsyncMock(),
    )
    monkeypatch.setattr(deletion_mod, "verify_password", _ok_verify)
    user = _build_user()

    await svc.delete(user, "x")
    passkey_repo.delete_all_by_user_id.assert_awaited_once_with(user.id)


async def test_service_audits_deletion(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, _, _, _, audit = _build_service()
    monkeypatch.setattr(deletion_mod, "verify_password", _ok_verify)
    user = _build_user()

    await svc.delete(user, "x")

    audit.record.assert_awaited_once()
    kwargs = audit.record.call_args.kwargs
    assert kwargs["action"] == AuditAction.ACCOUNT_DELETED
    assert kwargs["actor_id"] == user.id


async def test_service_audit_failure_does_not_break_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc, _, _, _, audit = _build_service()
    audit.record.side_effect = RuntimeError("audit down")
    monkeypatch.setattr(deletion_mod, "verify_password", _ok_verify)
    user = _build_user()

    await svc.delete(user, "x")
    assert user.deleted_at is not None
