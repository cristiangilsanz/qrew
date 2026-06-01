"""Tests for the admin user listing endpoint at GET /v1/admin/users."""

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
_PAGINATE = "com.qode.qrew.v1.service.routers.admin.users.cursor_paginate"


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
    with patch(_PAGINATE, new=AsyncMock(return_value=(users, None))):
        response = await client.get(_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is None


async def test_list_users_returns_user_fields(client: AsyncClient) -> None:
    with patch(_PAGINATE, new=AsyncMock(return_value=([_mock_user_row()], None))):
        response = await client.get(_ENDPOINT)

    user = response.json()["items"][0]
    assert user["email"] == "user@example.com"
    assert user["full_name"] == "Test User"
    assert user["kyc_status"] == KycStatus.approved
    assert user["email_verified"] is True
    assert user["phone_verified"] is True
    assert user["is_admin"] is False
    assert "id" in user
    assert "created_at" in user


async def test_list_users_empty_result(client: AsyncClient) -> None:
    with patch(_PAGINATE, new=AsyncMock(return_value=([], None))):
        response = await client.get(_ENDPOINT)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["next_cursor"] is None


async def test_list_users_returns_next_cursor_when_more_pages(
    client: AsyncClient,
) -> None:
    users = [_mock_user_row()]
    with patch(_PAGINATE, new=AsyncMock(return_value=(users, "next-token"))):
        response = await client.get(_ENDPOINT)

    assert response.json()["next_cursor"] == "next-token"


async def test_list_users_passes_search_param_to_repo(client: AsyncClient) -> None:
    with (
        patch(_USER_REPO) as mock_repo_cls,
        patch(_PAGINATE, new=AsyncMock(return_value=([], None))),
    ):
        mock_repo_cls.return_value.search_query = MagicMock(return_value=MagicMock())
        await client.get(_ENDPOINT, params={"search": "alice"})

    kwargs = mock_repo_cls.return_value.search_query.call_args.kwargs
    assert kwargs["search"] == "alice"


async def test_list_users_passes_kyc_status_filter(client: AsyncClient) -> None:
    with (
        patch(_USER_REPO) as mock_repo_cls,
        patch(_PAGINATE, new=AsyncMock(return_value=([], None))),
    ):
        mock_repo_cls.return_value.search_query = MagicMock(return_value=MagicMock())
        await client.get(_ENDPOINT, params={"kyc_status": "pending"})

    kwargs = mock_repo_cls.return_value.search_query.call_args.kwargs
    assert kwargs["kyc_status"] == KycStatus.pending


async def test_list_users_requires_admin(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_admin_user, None)

    response = await client.get(_ENDPOINT)

    assert response.status_code == 401
