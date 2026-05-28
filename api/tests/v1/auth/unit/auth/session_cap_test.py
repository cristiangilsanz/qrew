"""Tests for the per-user session cap enforcer."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.services.auth.logout import BLACKLIST_JTI_PREFIX
from com.qode.qrew.v1.service.services.auth.session_cap import SessionCapEnforcer
from com.qode.qrew.v1.service.settings import settings


def _victim(jti: str) -> MagicMock:
    v = MagicMock()
    v.id = uuid.uuid4()
    v.jti = jti
    return v


def _build(
    *,
    count: int,
    victims: list[MagicMock] | None = None,
    with_redis: bool = True,
) -> tuple[SessionCapEnforcer, AsyncMock, AsyncMock, AsyncMock]:
    session_repo = AsyncMock()
    session_repo.count_by_user_id = AsyncMock(return_value=count)
    session_repo.get_oldest_by_user_id = AsyncMock(return_value=victims or [])
    session_repo.delete_by_jti = AsyncMock()

    audit = AsyncMock()
    audit.record = AsyncMock()

    redis = AsyncMock()
    redis.setex = AsyncMock()

    enforcer = SessionCapEnforcer(session_repo, audit, redis if with_redis else None)
    return enforcer, session_repo, redis, audit


async def test_no_eviction_when_under_cap() -> None:
    enforcer, session_repo, redis, audit = _build(count=settings.max_sessions_per_user)
    await enforcer.enforce(uuid.uuid4())
    session_repo.get_oldest_by_user_id.assert_not_awaited()
    redis.setex.assert_not_awaited()
    audit.record.assert_not_awaited()


async def test_evicts_one_when_one_over_cap() -> None:
    victim = _victim("old-jti")
    enforcer, session_repo, redis, _audit = _build(
        count=settings.max_sessions_per_user + 1, victims=[victim]
    )
    user_id = uuid.uuid4()
    await enforcer.enforce(user_id)
    session_repo.get_oldest_by_user_id.assert_awaited_once_with(user_id, 1)
    session_repo.delete_by_jti.assert_awaited_once_with("old-jti")
    redis.setex.assert_awaited_once()
    args = redis.setex.call_args.args
    assert args[0] == BLACKLIST_JTI_PREFIX + "old-jti"
    assert args[1] == settings.refresh_token_expire_days * 86400


async def test_evicts_multiple_when_multiple_over_cap() -> None:
    victims = [_victim("a"), _victim("b"), _victim("c")]
    enforcer, session_repo, redis, _audit = _build(
        count=settings.max_sessions_per_user + 3, victims=victims
    )
    await enforcer.enforce(uuid.uuid4())
    session_repo.get_oldest_by_user_id.assert_awaited_once()
    args = session_repo.get_oldest_by_user_id.call_args.args
    assert args[1] == 3
    assert session_repo.delete_by_jti.await_count == 3
    assert redis.setex.await_count == 3


async def test_audit_logged_for_each_eviction() -> None:
    victims = [_victim("j1"), _victim("j2")]
    enforcer, _repo, _redis, audit = _build(
        count=settings.max_sessions_per_user + 2, victims=victims
    )
    user_id = uuid.uuid4()
    await enforcer.enforce(user_id)
    assert audit.record.await_count == 2
    for call in audit.record.await_args_list:
        assert call.kwargs["action"] == AuditAction.SESSION_EVICTED
        assert call.kwargs["actor_id"] == user_id
        assert call.kwargs["payload"]["reason"] == "session_cap"
        assert call.kwargs["payload"]["jti"] in {"j1", "j2"}


async def test_no_op_when_cap_is_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_sessions_per_user", 0)
    enforcer, session_repo, _redis, _audit = _build(count=99)
    await enforcer.enforce(uuid.uuid4())
    session_repo.count_by_user_id.assert_not_awaited()


async def test_eviction_skips_redis_when_redis_missing() -> None:
    victim = _victim("solo")
    enforcer, session_repo, _redis, audit = _build(
        count=settings.max_sessions_per_user + 1,
        victims=[victim],
        with_redis=False,
    )
    await enforcer.enforce(uuid.uuid4())
    session_repo.delete_by_jti.assert_awaited_once_with("solo")
    audit.record.assert_awaited_once()
