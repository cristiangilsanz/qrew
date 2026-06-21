import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.identity.services.application.authentication.login.guards.lockout import (
    LoginLockoutError,
    LoginLockoutService,
)

_MOD = "com.qode.qrew.v1.identity.services.application.authentication.login.guards.lockout"
_PATCH_SETTINGS = f"{_MOD}.settings"


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(
        login_max_attempts=5,
        login_lockout_base_seconds=300,
    )


def _make_svc() -> tuple[LoginLockoutService, MagicMock, AsyncMock]:
    redis = MagicMock()
    redis.ttl = AsyncMock(return_value=0)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    audit = AsyncMock()
    audit.record = AsyncMock()
    svc = LoginLockoutService(redis=redis, audit=audit)
    return svc, redis, audit


class TestDurationForAttempts:
    def test_below_first_threshold_returns_none(self) -> None:
        with patch(_PATCH_SETTINGS, _fake_settings()):
            assert LoginLockoutService._duration_for_attempts(4) is None

    def test_first_threshold_returns_base(self) -> None:
        with patch(_PATCH_SETTINGS, _fake_settings()):
            assert LoginLockoutService._duration_for_attempts(5) == 300

    def test_second_threshold_returns_6x(self) -> None:
        with patch(_PATCH_SETTINGS, _fake_settings()):
            assert LoginLockoutService._duration_for_attempts(10) == 1800

    def test_third_threshold_returns_288x(self) -> None:
        with patch(_PATCH_SETTINGS, _fake_settings()):
            assert LoginLockoutService._duration_for_attempts(20) == 300 * 288

    def test_between_thresholds_returns_none(self) -> None:
        with patch(_PATCH_SETTINGS, _fake_settings()):
            assert LoginLockoutService._duration_for_attempts(7) is None


class TestCheckNotLocked:
    async def test_passes_when_no_lock(self) -> None:
        svc, redis, _ = _make_svc()
        redis.ttl = AsyncMock(return_value=0)
        await svc.check_not_locked(uuid.uuid4())

    async def test_passes_when_ttl_negative(self) -> None:
        svc, redis, _ = _make_svc()
        redis.ttl = AsyncMock(return_value=-1)
        await svc.check_not_locked(uuid.uuid4())

    async def test_raises_when_locked(self) -> None:
        svc, redis, _ = _make_svc()
        redis.ttl = AsyncMock(return_value=120)
        with pytest.raises(LoginLockoutError) as exc_info:
            await svc.check_not_locked(uuid.uuid4())
        assert exc_info.value.retry_after_seconds == 120


class TestRecordFailure:
    async def test_no_lockout_below_threshold(self) -> None:
        svc, redis, audit = _make_svc()
        redis.incr = AsyncMock(return_value=3)
        with patch(_PATCH_SETTINGS, _fake_settings()):
            await svc.record_failure(uuid.uuid4())
        redis.setex.assert_not_awaited()

    async def test_lockout_triggered_at_threshold(self) -> None:
        svc, redis, audit = _make_svc()
        redis.incr = AsyncMock(return_value=5)
        with patch(_PATCH_SETTINGS, _fake_settings()):
            await svc.record_failure(uuid.uuid4(), ip_address="1.2.3.4")
        redis.setex.assert_awaited_once()
        call_args = redis.setex.call_args
        assert call_args.args[1] == 300

    async def test_expire_set_on_first_attempt(self) -> None:
        svc, redis, _ = _make_svc()
        redis.incr = AsyncMock(return_value=1)
        with patch(_PATCH_SETTINGS, _fake_settings()):
            await svc.record_failure(uuid.uuid4())
        redis.expire.assert_awaited_once()

    async def test_audit_swallowed_on_failure(self) -> None:
        svc, redis, audit = _make_svc()
        redis.incr = AsyncMock(return_value=5)
        audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch(_PATCH_SETTINGS, _fake_settings()):
            await svc.record_failure(uuid.uuid4())


class TestReset:
    async def test_deletes_both_keys(self) -> None:
        svc, redis, _ = _make_svc()
        user_id = uuid.uuid4()
        await svc.reset(user_id)
        redis.delete.assert_awaited_once()
        key_args = redis.delete.call_args.args
        assert any(str(user_id) in k for k in key_args)


class TestAdminUnlock:
    async def test_clears_lock_and_records_audit(self) -> None:
        svc, redis, audit = _make_svc()
        user_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        await svc.admin_unlock(user_id, admin_id)
        redis.delete.assert_awaited_once()
        audit.record.assert_awaited_once()

    async def test_audit_failure_is_swallowed(self) -> None:
        svc, redis, audit = _make_svc()
        audit.record = AsyncMock(side_effect=RuntimeError("down"))
        await svc.admin_unlock(uuid.uuid4(), uuid.uuid4())
