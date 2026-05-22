"""Tests for POST /v1/admin/kyc/{user_id}/review."""

import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_admin_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.user import KycStatus
from com.qode.qrew.v1.service.routers.admin import get_kyc_review_service
from com.qode.qrew.v1.service.services.kyc_review import KycReviewError

_USER_ID = str(uuid.uuid4())
_ENDPOINT = f"/v1/admin/kyc/{_USER_ID}/review"


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _mock_admin() -> MagicMock:
    admin = MagicMock()
    admin.is_admin = True
    return admin


def _mock_reviewed_user(status: KycStatus) -> MagicMock:
    user = MagicMock()
    user.id = uuid.UUID(_USER_ID)
    user.kyc_status = status
    return user


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.review = AsyncMock(return_value=_mock_reviewed_user(KycStatus.approved))
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_kyc_review_service] = lambda: mock_service
    app.dependency_overrides[get_admin_user] = _mock_admin
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_approve_returns_200_with_approved_status(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    response = await client.post(_ENDPOINT, json={"action": "approve"})

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["kyc_status"] == "approved"
    assert body["user_id"] == _USER_ID


async def test_reject_returns_200_with_rejected_status(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.review.return_value = _mock_reviewed_user(KycStatus.rejected)

    # When
    response = await client.post(
        _ENDPOINT, json={"action": "reject", "reason": "Blurry document"}
    )

    # Then
    assert response.status_code == 200
    assert response.json()["kyc_status"] == "rejected"


async def test_calls_service_with_correct_args(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    await client.post(
        _ENDPOINT, json={"action": "reject", "reason": "Could not verify"}
    )

    # Then
    mock_service.review.assert_awaited_once()
    call_kwargs = mock_service.review.call_args
    assert call_kwargs.args[1].value == "reject"
    assert call_kwargs.args[2] == "Could not verify"


async def test_reason_is_optional(client: AsyncClient, mock_service: AsyncMock) -> None:
    # When
    response = await client.post(_ENDPOINT, json={"action": "approve"})

    # Then
    assert response.status_code == 200


# ── Error cases ───────────────────────────────────────────────────────────────


async def test_returns_400_when_user_not_found(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.review.side_effect = KycReviewError("User not found", field="user_id")

    # When
    response = await client.post(_ENDPOINT, json={"action": "approve"})

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "user_id"


async def test_returns_400_when_kyc_not_pending(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.review.side_effect = KycReviewError(
        "KYC is not pending (current status: approved)", field="kyc_status"
    )

    # When
    response = await client.post(_ENDPOINT, json={"action": "approve"})

    # Then
    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "kyc_status"


# ── Auth ──────────────────────────────────────────────────────────────────────


async def test_returns_403_for_non_admin(client: AsyncClient) -> None:
    # Given
    app.dependency_overrides[get_admin_user] = lambda: (_ for _ in ()).throw(
        __import__("fastapi").HTTPException(
            status_code=403,
            detail={"message": "Admin access required", "field": None},
        )
    )

    # When
    response = await client.post(_ENDPOINT, json={"action": "approve"})

    # Then
    assert response.status_code == 403


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_invalid_action(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json={"action": "delete"})

    # Then
    assert response.status_code == 422


async def test_rejects_missing_action(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT, json={})

    # Then
    assert response.status_code == 422


async def test_rejects_reason_too_long(client: AsyncClient) -> None:
    # When
    response = await client.post(
        _ENDPOINT, json={"action": "reject", "reason": "x" * 501}
    )

    # Then
    assert response.status_code == 422
