"""Tests for admin user listing endpoint:
GET /v1/admin/users
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth.auth import get_admin_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.auth.user import KycStatus

_ENDPOINT = "/v1/admin/users"
_USER_REPO = "com.qode.qrew.v1.service.routers.admin.users.UserRepository"


def _mock_admin() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.is_admin = True
    return user


def _mock_user_row(is_admin: bool = False) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "user@example.com"
    u.full_name = "Test User"
    u.kyc_status = KycStatus.approved
    u.email_verified = True
    u.phone_number_verified = True
    u.is_admin = is_admin
    u.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return u


@pytest.fixture(autouse=True)
def override_admin() -> Iterator[None]:
    app.dependency_overrides[get_admin_user] = _mock_admin
    yield
    app.dependency_overrides.clear()


async def test_list_users_returns_200(client: AsyncClient) -> None:
    users = [_mock_user_row(), _mock_user_row()]
    with patch(_USER_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.search_paginated = AsyncMock(return_value=(users, 2))

        response = await client.get(_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["users"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 20


async def test_list_users_returns_user_fields(client: AsyncClient) -> None:
    with patch(_USER_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.search_paginated = AsyncMock(
            return_value=([_mock_user_row()], 1)
        )

        response = await client.get(_ENDPOINT)

    user = response.json()["users"][0]
    assert user["email"] == "user@example.com"
    assert user["full_name"] == "Test User"
    assert user["kyc_status"] == KycStatus.approved
    assert user["email_verified"] is True
    assert user["phone_verified"] is True
    assert user["is_admin"] is False
    assert "id" in user
    assert "created_at" in user


async def test_list_users_empty_result(client: AsyncClient) -> None:
    with patch(_USER_REPO) as mock_repo_cls:
        mock_repo_cls.return_value.search_paginated = AsyncMock(return_value=([], 0))

        response = await client.get(_ENDPOINT)

    assert response.status_code == 200
    assert response.json()["users"] == []
    assert response.json()["total"] == 0


async def test_list_users_passes_pagination_params(client: AsyncClient) -> None:
    with patch(_USER_REPO) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.search_paginated = AsyncMock(return_value=([], 0))

        await client.get(_ENDPOINT, params={"page": 3, "page_size": 50})

        mock_repo.search_paginated.assert_awaited_once_with(3, 50, None, None)


async def test_list_users_passes_search_param(client: AsyncClient) -> None:
    with patch(_USER_REPO) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.search_paginated = AsyncMock(return_value=([], 0))

        await client.get(_ENDPOINT, params={"search": "alice"})

        call_args = mock_repo.search_paginated.call_args[0]
        assert call_args[2] == "alice"


async def test_list_users_passes_kyc_status_filter(client: AsyncClient) -> None:
    with patch(_USER_REPO) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.search_paginated = AsyncMock(return_value=([], 0))

        await client.get(_ENDPOINT, params={"kyc_status": "pending"})

        call_args = mock_repo.search_paginated.call_args[0]
        assert call_args[3] == KycStatus.pending


async def test_list_users_requires_admin(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_admin_user, None)

    response = await client.get(_ENDPOINT)

    assert response.status_code == 401
