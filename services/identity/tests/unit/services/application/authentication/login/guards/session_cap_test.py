import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from com.qode.qrew.v1.identity.services.application.authentication.login.guards.session_cap import (
    SessionCapEnforcer,
)

_MOD = "com.qode.qrew.v1.identity.services.application.authentication.login.guards.session_cap"
_PATCH_SETTINGS = f"{_MOD}.settings"


def _fake_settings(*, cap: int = 3) -> SimpleNamespace:
    return SimpleNamespace(max_sessions_per_user=cap, refresh_token_expire_days=7)


def _make_enforcer() -> tuple[SessionCapEnforcer, MagicMock, AsyncMock]:
    session_repo = MagicMock()
    session_repo.count_by_user_id = AsyncMock(return_value=0)
    session_repo.get_oldest_by_user_id = AsyncMock(return_value=[])
    session_repo.delete_by_jti = AsyncMock()

    audit = AsyncMock()
    audit.record = AsyncMock()

    redis = MagicMock()
    redis.setex = AsyncMock()

    enforcer = SessionCapEnforcer(session_repo=session_repo, audit=audit, redis=redis)
    return enforcer, session_repo, audit


class TestSessionCapEnforcer:
    async def test_cap_zero_is_disabled(self) -> None:
        enforcer, session_repo, _ = _make_enforcer()
        with patch(_PATCH_SETTINGS, _fake_settings(cap=0)):
            await enforcer.enforce(uuid.uuid4())
        session_repo.count_by_user_id.assert_not_awaited()

    async def test_within_cap_does_nothing(self) -> None:
        enforcer, session_repo, _ = _make_enforcer()
        session_repo.count_by_user_id = AsyncMock(return_value=2)
        with patch(_PATCH_SETTINGS, _fake_settings(cap=3)):
            await enforcer.enforce(uuid.uuid4())
        session_repo.get_oldest_by_user_id.assert_not_awaited()

    async def test_at_cap_does_nothing(self) -> None:
        enforcer, session_repo, _ = _make_enforcer()
        session_repo.count_by_user_id = AsyncMock(return_value=3)
        with patch(_PATCH_SETTINGS, _fake_settings(cap=3)):
            await enforcer.enforce(uuid.uuid4())
        session_repo.get_oldest_by_user_id.assert_not_awaited()

    async def test_over_cap_evicts_oldest(self) -> None:
        enforcer, session_repo, audit = _make_enforcer()
        victim = SimpleNamespace(id=uuid.uuid4(), jti="old-jti")
        session_repo.count_by_user_id = AsyncMock(return_value=4)
        session_repo.get_oldest_by_user_id = AsyncMock(return_value=[victim])
        with patch(_PATCH_SETTINGS, _fake_settings(cap=3)):
            await enforcer.enforce(uuid.uuid4())
        session_repo.delete_by_jti.assert_awaited_once_with("old-jti")

    async def test_evicted_jti_is_blacklisted(self) -> None:
        enforcer, session_repo, _ = _make_enforcer()
        victim = SimpleNamespace(id=uuid.uuid4(), jti="evicted-jti")
        session_repo.count_by_user_id = AsyncMock(return_value=4)
        session_repo.get_oldest_by_user_id = AsyncMock(return_value=[victim])
        with patch(_PATCH_SETTINGS, _fake_settings(cap=3)):
            await enforcer.enforce(uuid.uuid4())
        enforcer._redis.setex.assert_awaited_once()
        key = enforcer._redis.setex.call_args.args[0]
        assert "evicted-jti" in key

    async def test_audit_failure_does_not_propagate(self) -> None:
        enforcer, session_repo, audit = _make_enforcer()
        victim = SimpleNamespace(id=uuid.uuid4(), jti="jti")
        session_repo.count_by_user_id = AsyncMock(return_value=4)
        session_repo.get_oldest_by_user_id = AsyncMock(return_value=[victim])
        audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch(_PATCH_SETTINGS, _fake_settings(cap=3)):
            await enforcer.enforce(uuid.uuid4())
