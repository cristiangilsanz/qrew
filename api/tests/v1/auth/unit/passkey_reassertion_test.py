"""Tests for POST /v1/auth/passkey/assert/begin and /complete."""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.auth import (
    get_current_session,
    get_current_user,
)
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.routers.auth import get_passkey_service
from com.qode.qrew.v1.service.services import passkey as passkey_module
from com.qode.qrew.v1.service.services.passkey import PasskeyError, PasskeyService

_BEGIN_ENDPOINT = "/v1/auth/passkey/assert/begin"
_COMPLETE_ENDPOINT = "/v1/auth/passkey/assert/complete"

_COMPLETE_PAYLOAD: dict[str, object] = {
    "id": "Y2hlY2tNZQ",
    "rawId": "Y2hlY2tNZQ",
    "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0In0",
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAABA",
        "signature": "MEYCIQDy0K2sGzrq7yGnxUBRyqvOBf5eRaKqMSuTvp6r1j8HqQ",
    },
    "type": "public-key",
}

_FAKE_OPTIONS = json.dumps(
    {"challenge": "Y2hhbGxlbmdl", "rpId": "localhost", "userVerification": "required"}
)


def _mock_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    return u


def _mock_session() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.jti = str(uuid.uuid4())
    return s


@pytest.fixture
def mock_service() -> AsyncMock:
    asserted_at = datetime.now(UTC)
    service = AsyncMock()
    service.begin_reassertion = AsyncMock(return_value=_FAKE_OPTIONS)
    service.complete_reassertion = AsyncMock(return_value=asserted_at)
    return service


@pytest.fixture(autouse=True)
def override_dependencies(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_passkey_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_current_session] = _mock_session
    yield
    app.dependency_overrides.clear()


# ── Happy paths ───────────────────────────────────────────────────────────────


async def test_begin_returns_200_with_options(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_BEGIN_ENDPOINT)
    assert response.status_code == 200
    body = response.json()
    assert body["options"] == _FAKE_OPTIONS
    mock_service.begin_reassertion.assert_awaited_once()


async def test_complete_returns_200_with_asserted_at(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "asserted_at" in body
    assert "access_token" not in body
    assert "refresh_token" not in body
    mock_service.complete_reassertion.assert_awaited_once()


async def test_begin_passes_session_jti_to_service(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    await client.post(_BEGIN_ENDPOINT)
    args = mock_service.begin_reassertion.call_args.args
    # args: (user, session_jti)
    assert isinstance(args[1], str)


# ── Validation ────────────────────────────────────────────────────────────────


async def test_complete_rejects_missing_payload(client: AsyncClient) -> None:
    response = await client.post(_COMPLETE_ENDPOINT, json={})
    assert response.status_code == 422


# ── Error mapping ─────────────────────────────────────────────────────────────


async def test_begin_returns_400_when_no_passkey_registered(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.begin_reassertion.side_effect = PasskeyError(
        "No passkey registered for this account"
    )
    response = await client.post(_BEGIN_ENDPOINT)
    assert response.status_code == 400


async def test_complete_returns_400_when_challenge_expired(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_reassertion.side_effect = PasskeyError(
        "Re-assertion challenge expired. Please start again."
    )
    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_PAYLOAD)
    assert response.status_code == 400


async def test_complete_returns_400_when_verification_fails(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.complete_reassertion.side_effect = PasskeyError(
        "Passkey re-assertion failed. Please try again."
    )
    response = await client.post(_COMPLETE_ENDPOINT, json=_COMPLETE_PAYLOAD)
    assert response.status_code == 400


# ── Service-level: PasskeyService.complete_reassertion stamps the session ─────


async def test_service_stamps_last_asserted_at(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete_reassertion calls session_repo.update_last_asserted_at on success."""

    user = MagicMock()
    user.id = uuid.uuid4()
    session = MagicMock()
    session.id = uuid.uuid4()
    session.jti = str(uuid.uuid4())

    credential = MagicMock()
    credential.user_id = user.id
    credential.sign_count = 0
    credential.public_key = b"k"

    passkey_repo = AsyncMock()
    passkey_repo.get_by_credential_id = AsyncMock(return_value=credential)
    passkey_repo.save = AsyncMock(return_value=credential)

    session_repo = AsyncMock()
    session_repo.update_last_asserted_at = AsyncMock()

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"raw_challenge")
    redis.delete = AsyncMock()

    audit = AsyncMock()

    verify_result = MagicMock()
    verify_result.new_sign_count = 1

    def _fake_verify(**_kwargs: object) -> MagicMock:
        return verify_result

    def _fake_decode(v: str | None) -> bytes:
        return v.encode() if v else b""

    monkeypatch.setattr(
        passkey_module.webauthn, "verify_authentication_response", _fake_verify
    )
    monkeypatch.setattr(passkey_module, "base64url_to_bytes", _fake_decode)

    svc = PasskeyService(passkey_repo, redis, AsyncMock(), audit, session_repo)
    request = MagicMock()
    request.raw_id = "Y2hlY2tNZQ"
    request.id = "Y2hlY2tNZQ"
    request.response.client_data_json = "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0In0"
    request.response.authenticator_data = "SZYN5YgOjGh0NBcPZHZgW4"
    request.response.signature = "MEYCIQDy0K2sGzrq7yGnxUBRyqvOBf5eRaKqMSuTvp6r1j8HqQ"
    request.response.user_handle = None

    result = await svc.complete_reassertion(user, session, request)

    assert isinstance(result, datetime)
    session_repo.update_last_asserted_at.assert_awaited_once()
    args = session_repo.update_last_asserted_at.call_args.args
    assert args[0] == session.jti


async def test_service_raises_when_credential_belongs_to_other_user() -> None:

    user = MagicMock()
    user.id = uuid.uuid4()
    session = MagicMock()
    session.jti = str(uuid.uuid4())

    credential = MagicMock()
    credential.user_id = uuid.uuid4()  # different user

    passkey_repo = AsyncMock()
    passkey_repo.get_by_credential_id = AsyncMock(return_value=credential)

    svc = PasskeyService(
        passkey_repo, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    )
    request = MagicMock()
    request.raw_id = "Y2hlY2tNZQ"

    with pytest.raises(PasskeyError, match="not recognised"):
        await svc.complete_reassertion(user, session, request)


async def test_service_raises_when_challenge_missing() -> None:

    user = MagicMock()
    user.id = uuid.uuid4()
    session = MagicMock()
    session.jti = str(uuid.uuid4())

    credential = MagicMock()
    credential.user_id = user.id

    passkey_repo = AsyncMock()
    passkey_repo.get_by_credential_id = AsyncMock(return_value=credential)

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)

    svc = PasskeyService(passkey_repo, redis, AsyncMock(), AsyncMock(), AsyncMock())
    request = MagicMock()
    request.raw_id = "Y2hlY2tNZQ"

    with pytest.raises(PasskeyError, match="challenge expired"):
        await svc.complete_reassertion(user, session, request)


# ── PasskeyService.begin_reassertion stores 30s challenge ─────────────────────


async def test_begin_reassertion_stores_30s_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    user = MagicMock()
    user.id = uuid.uuid4()
    session_jti = str(uuid.uuid4())

    credential = MagicMock()
    credential.credential_id = b"cred"

    passkey_repo = AsyncMock()
    passkey_repo.get_all_by_user_id = AsyncMock(return_value=[credential])

    redis = AsyncMock()
    redis.set = AsyncMock()

    options = MagicMock()
    options.challenge = b"challenge"

    def _fake_gen(**_kwargs: object) -> MagicMock:
        return options

    def _fake_to_json(_opts: object) -> str:
        return _FAKE_OPTIONS

    monkeypatch.setattr(
        passkey_module.webauthn, "generate_authentication_options", _fake_gen
    )
    monkeypatch.setattr(passkey_module.webauthn, "options_to_json", _fake_to_json)

    svc = PasskeyService(passkey_repo, redis, AsyncMock(), AsyncMock(), AsyncMock())
    result = await svc.begin_reassertion(user, session_jti)
    assert result == _FAKE_OPTIONS
    redis.set.assert_awaited_once()
    kwargs = redis.set.call_args.kwargs
    assert kwargs["ex"] == 30


async def test_begin_reassertion_raises_when_no_passkey() -> None:

    user = MagicMock()
    user.id = uuid.uuid4()

    passkey_repo = AsyncMock()
    passkey_repo.get_all_by_user_id = AsyncMock(return_value=[])

    svc = PasskeyService(
        passkey_repo, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    )
    with pytest.raises(PasskeyError, match="No passkey"):
        await svc.begin_reassertion(user, str(uuid.uuid4()))
