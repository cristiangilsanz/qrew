"""Tests for auth dependency functions (core/auth.py)."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.auth.security import create_setup_token

_USER_ID = "00000000-0000-0000-0000-000000000001"


async def test_get_current_user_rejects_setup_token_with_403() -> None:
    """A setup-scoped token must be rejected with 403 by get_current_user."""
    token = create_setup_token(_USER_ID)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=AsyncMock())

    assert exc_info.value.status_code == 403
    detail: dict[str, str | None] = exc_info.value.detail  # type: ignore[assignment]
    assert "Setup not complete" in (detail["message"] or "")
