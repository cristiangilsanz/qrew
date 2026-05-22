"""Tests for POST /v1/auth/kyc/upload."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import get_setup_or_full_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.user import KycStatus
from com.qode.qrew.v1.service.routers.auth import get_kyc_service
from com.qode.qrew.v1.service.services.kyc import KycError

_ENDPOINT = "/v1/auth/kyc/upload"
_FAKE_DOCUMENT = b"fake-national-id-document-content"


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _mock_user() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.upload = AsyncMock(return_value=KycStatus.pending)
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_kyc_service] = lambda: mock_service
    app.dependency_overrides[get_setup_or_full_user] = _mock_user
    yield
    app.dependency_overrides.clear()


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_kyc_upload_returns_200(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    response = await client.post(
        _ENDPOINT,
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    # Then
    assert response.status_code == 200
    body = response.json()
    assert "submitted" in body["message"].lower()
    assert body["kyc_status"] == "pending"


async def test_kyc_upload_calls_service_with_content(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # When
    await client.post(
        _ENDPOINT,
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    # Then
    mock_service.upload.assert_awaited_once()
    call_args = mock_service.upload.call_args[0]
    assert call_args[1] == _FAKE_DOCUMENT


# ── Domain errors (400) ───────────────────────────────────────────────────────


async def test_returns_400_on_empty_document(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.upload.side_effect = KycError("Document cannot be empty")

    # When
    response = await client.post(
        _ENDPOINT,
        files={"document": ("id.jpg", b"", "image/jpeg")},
    )

    # Then
    assert response.status_code == 400


async def test_returns_400_on_oversized_document(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    # Given
    mock_service.upload.side_effect = KycError(
        "Document exceeds the maximum allowed size of 10 MB"
    )

    # When
    response = await client.post(
        _ENDPOINT,
        files={"document": ("id.jpg", _FAKE_DOCUMENT, "image/jpeg")},
    )

    # Then
    assert response.status_code == 400


# ── Input validation (422) ────────────────────────────────────────────────────


async def test_rejects_missing_file(client: AsyncClient) -> None:
    # When
    response = await client.post(_ENDPOINT)

    # Then
    assert response.status_code == 422
