"""Tests for per-refresh device-key signature on device-bound sessions."""

import base64
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.hashes import SHA256
from httpx import AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.session import Session
from com.qode.qrew.v1.service.routers.auth import get_refresh_service
from com.qode.qrew.v1.service.schemas.auth import RefreshResponse
from com.qode.qrew.v1.service.services.refresh import (
    RefreshError,
    RefreshService,
    decode_signature_header,
    signature_payload,
)

_REFRESH_ENDPOINT = "/v1/auth/refresh"


# ── signature_payload format ─────────────────────────────────────────────────


def test_signature_payload_format() -> None:
    assert signature_payload("jti-x", 1700000000) == b"jti-x|1700000000"


def test_decode_signature_header_handles_padding() -> None:
    raw_sig = b"abc"
    encoded = base64.urlsafe_b64encode(raw_sig).decode().rstrip("=")
    assert decode_signature_header(encoded) == raw_sig


def test_decode_signature_header_none() -> None:
    assert decode_signature_header(None) is None


def test_decode_signature_header_malformed_returns_none() -> None:
    assert decode_signature_header("!!!not-base64!!!") is None


# ── Route forwards X-Device-Signature ────────────────────────────────────────


@pytest.fixture
def mock_refresh_service() -> AsyncMock:
    s = AsyncMock()
    s.refresh = AsyncMock(
        return_value=RefreshResponse(access_token="a.b.c", refresh_token="d.e.f")
    )
    return s


@pytest.fixture(autouse=True)
def override(mock_refresh_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_refresh_service] = lambda: mock_refresh_service
    yield
    app.dependency_overrides.clear()


async def test_refresh_route_forwards_signature_bytes(
    client: AsyncClient, mock_refresh_service: AsyncMock
) -> None:
    sig = base64.urlsafe_b64encode(b"raw-sig-bytes").decode().rstrip("=")
    await client.post(
        _REFRESH_ENDPOINT,
        json={"refresh_token": "tok"},
        headers={"X-Device-Signature": sig},
    )
    args = mock_refresh_service.refresh.call_args.args
    assert args[1] == b"raw-sig-bytes"


async def test_refresh_route_passes_none_when_header_missing(
    client: AsyncClient, mock_refresh_service: AsyncMock
) -> None:
    await client.post(_REFRESH_ENDPOINT, json={"refresh_token": "tok"})
    args = mock_refresh_service.refresh.call_args.args
    assert args[1] is None


async def test_refresh_returns_401_when_service_rejects_signature(
    client: AsyncClient, mock_refresh_service: AsyncMock
) -> None:
    mock_refresh_service.refresh.side_effect = RefreshError(
        "Refresh device signature invalid"
    )
    response = await client.post(
        _REFRESH_ENDPOINT,
        json={"refresh_token": "tok"},
        headers={"X-Device-Signature": "AAAA"},
    )
    assert response.status_code == 401


# ── Service-level check_device_binding ───────────────────────────────────────


def _generate_keypair() -> tuple[ec.EllipticCurvePrivateKey, bytes]:
    key = ec.generate_private_key(ec.SECP256R1())
    pub_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return key, pub_der


def _build_service(
    *, session: Session | None, device: MagicMock | None = None
) -> tuple[RefreshService, AsyncMock]:
    session_repo = AsyncMock()
    session_repo.get_by_jti = AsyncMock(return_value=session)
    device_repo = AsyncMock()
    device_repo.get_by_id = AsyncMock(return_value=device)
    audit = AsyncMock()
    audit.record = AsyncMock()
    svc = RefreshService(
        AsyncMock(),
        AsyncMock(),
        audit,
        session_repo=session_repo,
        device_repo=device_repo,
    )
    return svc, audit


async def test_unbound_session_skips_signature_check() -> None:
    jti = str(uuid.uuid4())
    session = Session(id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=None)
    svc, _ = _build_service(session=session)
    result = await svc.check_device_binding(jti, int(time.time()), None, uuid.uuid4())
    assert result is None


async def test_bound_session_with_valid_signature_succeeds() -> None:
    key, pub_der = _generate_keypair()
    device_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    iat = int(time.time())

    session = Session(
        id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=device_id
    )
    device = MagicMock()
    device.public_key = pub_der
    device.revoked_at = None

    svc, _ = _build_service(session=session, device=device)

    sig = key.sign(signature_payload(jti, iat), ec.ECDSA(SHA256()))
    result = await svc.check_device_binding(jti, iat, sig, uuid.uuid4())
    assert result == device_id


async def test_bound_session_with_wrong_signature_raises_and_audits() -> None:
    _key, pub_der = _generate_keypair()
    other_key, _ = _generate_keypair()
    jti = str(uuid.uuid4())
    iat = int(time.time())

    session = Session(
        id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=uuid.uuid4()
    )
    device = MagicMock()
    device.public_key = pub_der
    device.revoked_at = None

    svc, audit = _build_service(session=session, device=device)

    bad_sig = other_key.sign(signature_payload(jti, iat), ec.ECDSA(SHA256()))
    with pytest.raises(RefreshError, match="device signature invalid"):
        await svc.check_device_binding(jti, iat, bad_sig, uuid.uuid4())

    audit.record.assert_awaited_once()
    kwargs = audit.record.call_args.kwargs
    assert kwargs["action"] == AuditAction.REFRESH_SIGNATURE_INVALID


async def test_bound_session_with_missing_signature_raises_and_audits() -> None:
    jti = str(uuid.uuid4())
    iat = int(time.time())

    session = Session(
        id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=uuid.uuid4()
    )
    svc, audit = _build_service(session=session)

    with pytest.raises(RefreshError, match="requires a device signature"):
        await svc.check_device_binding(jti, iat, None, uuid.uuid4())
    audit.record.assert_awaited_once()


async def test_bound_session_rejects_when_device_revoked() -> None:
    key, pub_der = _generate_keypair()
    jti = str(uuid.uuid4())
    iat = int(time.time())

    session = Session(
        id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=uuid.uuid4()
    )
    device = MagicMock()
    device.public_key = pub_der
    device.revoked_at = datetime.now(UTC)

    svc, _ = _build_service(session=session, device=device)
    sig = key.sign(signature_payload(jti, iat), ec.ECDSA(SHA256()))

    with pytest.raises(RefreshError, match="no longer valid"):
        await svc.check_device_binding(jti, iat, sig, uuid.uuid4())


async def test_payload_includes_iat_so_signature_doesnt_replay_to_other_iat() -> None:
    """A signature over (jti, iat=A) must not validate against (jti, iat=B)."""
    key, pub_der = _generate_keypair()
    jti = str(uuid.uuid4())
    iat_a = int(time.time())
    iat_b = iat_a + 1

    session = Session(
        id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=uuid.uuid4()
    )
    device = MagicMock()
    device.public_key = pub_der
    device.revoked_at = None

    svc, _ = _build_service(session=session, device=device)
    sig_a = key.sign(signature_payload(jti, iat_a), ec.ECDSA(SHA256()))

    # Same signature, different iat → must reject
    with pytest.raises(RefreshError, match="device signature invalid"):
        await svc.check_device_binding(jti, iat_b, sig_a, uuid.uuid4())


async def test_unbound_session_ignores_signature_when_provided() -> None:
    """Sessions without device_id ignore the signature header (backwards compat)."""
    jti = str(uuid.uuid4())
    session = Session(id=uuid.uuid4(), user_id=uuid.uuid4(), jti=jti, device_id=None)
    svc, _ = _build_service(session=session)
    result = await svc.check_device_binding(
        jti, int(time.time()), b"any-bytes", uuid.uuid4()
    )
    assert result is None
