"""Tests for per-account login lockout and admin unlock."""

import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_admin_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.auth.user import KycStatus
from com.qode.qrew.v1.service.routers.admin import get_login_lockout_service
from com.qode.qrew.v1.service.routers.auth import get_login_service
from com.qode.qrew.v1.service.schemas.auth.auth import (
    LoginRequest,
    LoginResponse,
)
from com.qode.qrew.v1.service.services.auth import login as login_mod
from com.qode.qrew.v1.service.services.auth.login import LoginError, LoginService
from com.qode.qrew.v1.service.services.auth.login_lockout import (
    LoginLockoutError,
    LoginLockoutService,
)
from com.qode.qrew.v1.service.settings import settings

_LOGIN_ENDPOINT = "/v1/auth/login"
_LOGIN_PAYLOAD: dict[str, object] = {
    "email": "alice@example.com",
    "password": "Str0ng!P@ssw0rd",
}


def _mock_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_admin = True
    return u


@pytest.fixture
def mock_login_service() -> AsyncMock:
    s = AsyncMock()
    s.login = AsyncMock(return_value=LoginResponse(access_token="a.b.c"))
    return s


@pytest.fixture
def override_login(mock_login_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_login_service] = lambda: mock_login_service
    yield
    app.dependency_overrides.clear()


async def test_login_returns_429_with_retry_after_when_locked(
    client: AsyncClient,
    mock_login_service: AsyncMock,
    override_login: None,
) -> None:
    mock_login_service.login.side_effect = LoginLockoutError(
        "Account temporarily locked", retry_after_seconds=300
    )
    response = await client.post(_LOGIN_ENDPOINT, json=_LOGIN_PAYLOAD)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "300"
    body = response.json()
    assert "Invalid email or password" in str(body)


async def test_normal_login_failure_still_returns_401(
    client: AsyncClient,
    mock_login_service: AsyncMock,
    override_login: None,
) -> None:
    mock_login_service.login.side_effect = LoginError("Invalid email or password")
    response = await client.post(_LOGIN_ENDPOINT, json=_LOGIN_PAYLOAD)
    assert response.status_code == 401


def _service() -> tuple[LoginLockoutService, AsyncMock, AsyncMock]:
    redis = AsyncMock()
    redis.incr = AsyncMock()
    redis.expire = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.ttl = AsyncMock(return_value=0)
    audit = AsyncMock()
    audit.record = AsyncMock()
    return LoginLockoutService(redis, audit), redis, audit


async def test_check_not_locked_passes_when_no_lock() -> None:
    svc, redis, _ = _service()
    redis.ttl.return_value = 0
    await svc.check_not_locked(uuid.uuid4())


async def test_check_not_locked_raises_with_remaining_ttl() -> None:
    svc, redis, _ = _service()
    redis.ttl.return_value = 137
    with pytest.raises(LoginLockoutError) as exc:
        await svc.check_not_locked(uuid.uuid4())
    assert exc.value.retry_after_seconds == 137


async def test_record_failure_below_threshold_does_not_lock() -> None:
    svc, redis, audit = _service()
    redis.incr.return_value = settings.login_max_attempts - 1
    await svc.record_failure(uuid.uuid4(), "127.0.0.1")
    redis.setex.assert_not_awaited()
    audit.record.assert_not_awaited()


async def test_record_failure_at_first_threshold_locks_for_base() -> None:
    svc, redis, audit = _service()
    redis.incr.return_value = settings.login_max_attempts
    user_id = uuid.uuid4()
    await svc.record_failure(user_id, "127.0.0.1")
    redis.setex.assert_awaited_once()
    args = redis.setex.call_args.args
    assert args[0] == f"login:lock:{user_id}"
    assert args[1] == settings.login_lockout_base_seconds
    audit.record.assert_awaited_once()


async def test_record_failure_at_second_threshold_escalates() -> None:
    svc, redis, _ = _service()
    redis.incr.return_value = settings.login_max_attempts * 2
    await svc.record_failure(uuid.uuid4())
    args = redis.setex.call_args.args
    assert args[1] == settings.login_lockout_base_seconds * 6


async def test_record_failure_at_third_threshold_locks_for_24h_equivalent() -> None:
    svc, redis, _ = _service()
    redis.incr.return_value = settings.login_max_attempts * 4
    await svc.record_failure(uuid.uuid4())
    args = redis.setex.call_args.args
    assert args[1] == settings.login_lockout_base_seconds * 288


async def test_record_failure_between_thresholds_does_not_relock() -> None:
    svc, redis, _ = _service()
    redis.incr.return_value = settings.login_max_attempts + 1
    await svc.record_failure(uuid.uuid4())
    redis.setex.assert_not_awaited()


async def test_record_failure_first_attempt_sets_ttl_on_counter() -> None:
    svc, redis, _ = _service()
    redis.incr.return_value = 1
    await svc.record_failure(uuid.uuid4())
    redis.expire.assert_awaited_once()


async def test_reset_clears_both_keys() -> None:
    svc, redis, _ = _service()
    user_id = uuid.uuid4()
    await svc.reset(user_id)
    redis.delete.assert_awaited_once_with(
        f"login:failed:{user_id}", f"login:lock:{user_id}"
    )


async def test_admin_unlock_resets_and_audits() -> None:
    svc, redis, audit = _service()
    user_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    await svc.admin_unlock(user_id, admin_id)
    redis.delete.assert_awaited_once()
    audit.record.assert_awaited_once()
    kwargs = audit.record.call_args.kwargs
    assert kwargs["actor_id"] == admin_id


@pytest.fixture
def mock_lockout() -> AsyncMock:
    s = AsyncMock()
    s.admin_unlock = AsyncMock()
    return s


@pytest.fixture
def override_admin_lockout(mock_lockout: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_admin_user] = _mock_admin
    app.dependency_overrides[get_login_lockout_service] = lambda: mock_lockout
    yield
    app.dependency_overrides.clear()


async def test_admin_unlock_endpoint_returns_200(
    client: AsyncClient,
    mock_lockout: AsyncMock,
    override_admin_lockout: None,
) -> None:
    user_id = uuid.uuid4()
    response = await client.post(f"/v1/admin/users/{user_id}/unlock")
    assert response.status_code == 200
    body = response.json()
    assert "unlocked" in body["message"].lower()
    mock_lockout.admin_unlock.assert_awaited_once()


async def test_admin_unlock_endpoint_rejects_invalid_uuid(
    client: AsyncClient,
    mock_lockout: AsyncMock,
    override_admin_lockout: None,
) -> None:
    response = await client.post("/v1/admin/users/not-a-uuid/unlock")
    assert response.status_code == 422


async def test_login_service_resets_lockout_on_success() -> None:

    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.email_verified = True
    user.is_active = True
    user.phone_number_verified = True
    user.kyc_status = KycStatus.approved
    user.hashed_password = "hash"

    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    passkey_repo = AsyncMock()
    passkey_repo.has_passkey = AsyncMock(return_value=True)
    lockout = AsyncMock()
    lockout.check_not_locked = AsyncMock()
    lockout.reset = AsyncMock()
    lockout.record_failure = AsyncMock()

    svc = LoginService(repo, passkey_repo, AsyncMock(), lockout=lockout)

    with pytest.MonkeyPatch.context() as mp:

        def _ok(_p: str, _h: str) -> bool:
            return True

        mp.setattr(login_mod, "verify_password", _ok)
        await svc.login(LoginRequest(email="alice@example.com", password="x"))

    lockout.check_not_locked.assert_awaited_once_with(user.id)
    lockout.reset.assert_awaited_once_with(user.id)
    lockout.record_failure.assert_not_awaited()


async def test_login_service_records_failure_on_wrong_password() -> None:

    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.email_verified = True
    user.is_active = True
    user.hashed_password = "hash"

    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    lockout = AsyncMock()

    svc = LoginService(repo, AsyncMock(), AsyncMock(), lockout=lockout)

    with pytest.MonkeyPatch.context() as mp:

        def _bad(_p: str, _h: str) -> bool:
            return False

        mp.setattr(login_mod, "verify_password", _bad)
        with pytest.raises(LoginError):
            await svc.login(LoginRequest(email="alice@example.com", password="x"))

    lockout.record_failure.assert_awaited_once()


async def test_login_service_check_not_locked_raises_before_password_verify() -> None:

    user = MagicMock()
    user.id = uuid.uuid4()
    user.hashed_password = "hash"

    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    lockout = AsyncMock()
    lockout.check_not_locked = AsyncMock(
        side_effect=LoginLockoutError("locked", retry_after_seconds=10)
    )

    svc = LoginService(repo, AsyncMock(), AsyncMock(), lockout=lockout)

    with pytest.raises(LoginLockoutError):
        await svc.login(LoginRequest(email="alice@example.com", password="x"))
