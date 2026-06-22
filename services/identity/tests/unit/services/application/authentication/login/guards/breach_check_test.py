import uuid
from unittest.mock import AsyncMock, patch


from com.qode.qrew.v1.identity.services.application.authentication.login.guards.breach_check import (
    PasswordBreachChecker,
)

_MOD = "com.qode.qrew.v1.identity.services.application.authentication.login.guards.breach_check"
_PATCH_PWNED = f"{_MOD}.is_password_pwned"


def _make_checker() -> tuple[PasswordBreachChecker, AsyncMock]:
    audit = AsyncMock()
    audit.record = AsyncMock()
    checker = PasswordBreachChecker(audit=audit)
    return checker, audit


class TestPasswordBreachChecker:
    async def test_clean_password_returns_false(self) -> None:
        checker, audit = _make_checker()
        with patch(_PATCH_PWNED, new=AsyncMock(return_value=False)):
            result = await checker.is_compromised(uuid.uuid4(), "clean_pass", "1.2.3.4")
        assert result is False
        audit.record.assert_not_awaited()

    async def test_compromised_password_returns_true(self) -> None:
        checker, audit = _make_checker()
        with patch(_PATCH_PWNED, new=AsyncMock(return_value=True)):
            result = await checker.is_compromised(uuid.uuid4(), "leaked_pass", None)
        assert result is True
        audit.record.assert_awaited_once()

    async def test_hibp_error_returns_false(self) -> None:
        checker, audit = _make_checker()
        with patch(_PATCH_PWNED, new=AsyncMock(side_effect=Exception("network error"))):
            result = await checker.is_compromised(uuid.uuid4(), "any_pass", None)
        assert result is False

    async def test_audit_failure_does_not_propagate(self) -> None:
        checker, audit = _make_checker()
        audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch(_PATCH_PWNED, new=AsyncMock(return_value=True)):
            result = await checker.is_compromised(uuid.uuid4(), "leaked", None)
        assert result is True
