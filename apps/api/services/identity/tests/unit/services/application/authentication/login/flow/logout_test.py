import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jwt import ExpiredSignatureError, InvalidTokenError

from com.qode.qrew.v1.identity.services.application.authentication.login.flow.logout import (
    LogoutError,
    LogoutService,
)

_MOD = "com.qode.qrew.v1.identity.services.application.authentication.login.flow.logout"
_PATCH_DECODE = f"{_MOD}.decode_refresh_token"


def _make_svc(*, with_session_repo: bool = True) -> tuple[LogoutService, MagicMock, AsyncMock]:
    redis = MagicMock()
    redis.setex = AsyncMock()

    audit = AsyncMock()
    audit.record = AsyncMock()

    session_repo = MagicMock() if with_session_repo else None
    if session_repo:
        session_repo.delete_by_jti = AsyncMock()

    svc = LogoutService(redis=redis, audit=audit, session_repo=session_repo)
    return svc, redis, audit


def _valid_payload(*, jti: str = "test-jti") -> dict:
    exp = int((datetime.now(UTC) + timedelta(days=7)).timestamp())
    return {"type": "refresh", "jti": jti, "sub": str(uuid.uuid4()), "exp": exp}


class TestLogoutService:
    async def test_expired_token_returns_silently(self) -> None:
        svc, redis, audit = _make_svc()
        with patch(_PATCH_DECODE, side_effect=ExpiredSignatureError("expired")):
            await svc.logout("expired.token")
        redis.setex.assert_not_awaited()

    async def test_invalid_token_raises_logout_error(self) -> None:
        svc, _, _ = _make_svc()
        with (
            patch(_PATCH_DECODE, side_effect=InvalidTokenError("bad")),
            pytest.raises(LogoutError, match="Invalid refresh token"),
        ):
            await svc.logout("bad.token")

    async def test_wrong_token_type_raises(self) -> None:
        svc, _, _ = _make_svc()
        payload = {"type": "access", "jti": "j", "sub": str(uuid.uuid4()), "exp": 9999999999}
        with (
            patch(_PATCH_DECODE, return_value=payload),
            pytest.raises(LogoutError, match="Invalid token type"),
        ):
            await svc.logout("access.token")

    async def test_valid_token_blacklists_jti(self) -> None:
        svc, redis, _ = _make_svc()
        payload = _valid_payload(jti="my-jti")
        with patch(_PATCH_DECODE, return_value=payload):
            await svc.logout("valid.token")
        redis.setex.assert_awaited_once()
        key = redis.setex.call_args.args[0]
        assert "my-jti" in key

    async def test_valid_token_deletes_session(self) -> None:
        svc, _, _ = _make_svc(with_session_repo=True)
        payload = _valid_payload(jti="my-jti")
        with patch(_PATCH_DECODE, return_value=payload):
            await svc.logout("valid.token")
        svc._session_repo.delete_by_jti.assert_awaited_once_with("my-jti")

    async def test_no_session_repo_does_not_fail(self) -> None:
        svc, _, _ = _make_svc(with_session_repo=False)
        payload = _valid_payload()
        with patch(_PATCH_DECODE, return_value=payload):
            await svc.logout("valid.token")

    async def test_expired_token_does_not_blacklist(self) -> None:
        svc, redis, _ = _make_svc()
        payload = _valid_payload()
        payload["exp"] = int(datetime.now(UTC).timestamp()) - 100
        with patch(_PATCH_DECODE, return_value=payload):
            await svc.logout("valid.token")
        redis.setex.assert_not_awaited()

    async def test_audit_failure_is_swallowed(self) -> None:
        svc, _, audit = _make_svc()
        audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        payload = _valid_payload()
        with patch(_PATCH_DECODE, return_value=payload):
            await svc.logout("valid.token")
