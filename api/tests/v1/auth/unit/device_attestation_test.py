"""Tests for device integrity attestation."""

import base64
import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.hashes import SHA256
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.attestation import (
    AttestationResult,
    AttestationVerifierError,
    BypassVerifier,
)
from com.qode.qrew.v1.service.core.auth import get_current_user
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.routers.auth import get_device_attestation_service
from com.qode.qrew.v1.service.services.device_attestation import (
    ATTESTED_PREFIX,
    DeviceAttestationError,
    DeviceAttestationService,
    consume_attestation,
)
from com.qode.qrew.v1.service.services.device_binding import (
    DeviceBindingError,
    DeviceBindingService,
)
from com.qode.qrew.v1.service.settings import settings

_ENDPOINT = "/v1/auth/devices/attest"
_PAYLOAD: dict[str, object] = {"platform": "android", "token": "fake.jws.token"}


def _mock_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_admin = False
    return u


@pytest.fixture
def mock_service() -> AsyncMock:
    s = AsyncMock()
    s.attest = AsyncMock(return_value=AttestationResult(platform="android"))
    return s


@pytest.fixture(autouse=True)
def override(mock_service: AsyncMock) -> Iterator[None]:
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_device_attestation_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


# ── Route layer ───────────────────────────────────────────────────────────────


async def test_attest_returns_200(client: AsyncClient, mock_service: AsyncMock) -> None:
    response = await client.post(_ENDPOINT, json=_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["platform"] == "android"
    mock_service.attest.assert_awaited_once()


async def test_attest_rejects_unknown_platform(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={"platform": "windows", "token": "x"})
    assert response.status_code == 422


async def test_attest_rejects_empty_token(client: AsyncClient) -> None:
    response = await client.post(_ENDPOINT, json={"platform": "android", "token": ""})
    assert response.status_code == 422


async def test_attest_returns_403_when_verdict_negative(
    client: AsyncClient, mock_service: AsyncMock
) -> None:
    mock_service.attest.side_effect = DeviceAttestationError(
        "Device fails MEETS_DEVICE_INTEGRITY"
    )
    response = await client.post(_ENDPOINT, json=_PAYLOAD)
    assert response.status_code == 403


# ── Service layer ─────────────────────────────────────────────────────────────


def _build_service(
    *, has_challenge: bool = True, verifier: object | None = None
) -> tuple[DeviceAttestationService, AsyncMock, AsyncMock, AsyncMock]:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"nonce-abc" if has_challenge else None)
    redis.setex = AsyncMock()
    audit = AsyncMock()
    audit.record = AsyncMock()
    if verifier is None:
        verifier = AsyncMock()
        verifier.verify_android = AsyncMock(
            return_value=AttestationResult(platform="android")
        )
        verifier.verify_ios = AsyncMock(return_value=AttestationResult(platform="ios"))
    svc = DeviceAttestationService(verifier, redis, audit)  # type: ignore[arg-type]
    return svc, redis, audit, verifier  # type: ignore[return-value]


async def test_service_rejects_when_no_active_challenge() -> None:
    svc, _, _, _ = _build_service(has_challenge=False)
    with pytest.raises(DeviceAttestationError, match="No active bind challenge"):
        await svc.attest(uuid.uuid4(), "android", "tok")


async def test_service_passes_challenge_as_nonce() -> None:
    svc, _, _, verifier = _build_service()
    user_id = uuid.uuid4()
    await svc.attest(user_id, "android", "tok")
    args = verifier.verify_android.call_args.args  # type: ignore[union-attr]
    assert args[1] == "nonce-abc"


async def test_service_unsupported_platform() -> None:
    svc, _, _, _ = _build_service()
    with pytest.raises(DeviceAttestationError, match="Unsupported platform"):
        await svc.attest(uuid.uuid4(), "windows", "tok")


async def test_service_sets_redis_flag_on_success() -> None:
    svc, redis, _, _ = _build_service()
    user_id = uuid.uuid4()
    await svc.attest(user_id, "android", "tok")
    redis.setex.assert_awaited_once()
    args = redis.setex.call_args.args
    assert args[0] == f"{ATTESTED_PREFIX}{user_id}"


async def test_service_audits_success() -> None:
    svc, _, audit, _ = _build_service()
    await svc.attest(uuid.uuid4(), "android", "tok")
    audit.record.assert_awaited_once()
    assert audit.record.call_args.kwargs["action"] == AuditAction.DEVICE_ATTESTED


async def test_service_audits_failure_and_raises() -> None:
    verifier = AsyncMock()
    verifier.verify_android = AsyncMock(
        side_effect=AttestationVerifierError("emulator detected")
    )
    svc, _, audit, _ = _build_service(verifier=verifier)
    with pytest.raises(DeviceAttestationError, match="emulator detected"):
        await svc.attest(uuid.uuid4(), "android", "tok")
    audit.record.assert_awaited_once()
    assert (
        audit.record.call_args.kwargs["action"] == AuditAction.DEVICE_ATTESTATION_FAILED
    )


# ── consume_attestation helper ────────────────────────────────────────────────


async def test_consume_returns_skipped_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "attestation_enabled", False)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    result = await consume_attestation(redis, uuid.uuid4())
    assert result == "skipped"
    redis.get.assert_not_awaited()


async def test_consume_returns_none_when_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "attestation_enabled", True)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    result = await consume_attestation(redis, uuid.uuid4())
    assert result is None


async def test_consume_returns_platform_and_clears_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "attestation_enabled", True)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"android")
    redis.delete = AsyncMock()
    result = await consume_attestation(redis, uuid.uuid4())
    assert result == "android"
    redis.delete.assert_awaited_once()


# ── BypassVerifier ────────────────────────────────────────────────────────────


async def test_bypass_verifier_passes_anything() -> None:
    verifier = BypassVerifier()
    r1 = await verifier.verify_android("anything", "any-nonce")
    r2 = await verifier.verify_ios("anything", "any-nonce")
    assert r1.platform == "bypass"
    assert r2.platform == "bypass"


# ── bind/complete enforcement (uses real ECDSA P-256 key) ────────────────────


def _make_ecdsa_keypair_and_sig(message: bytes) -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    pub_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    sig = key.sign(message, ec.ECDSA(SHA256()))
    pub_b64 = base64.urlsafe_b64encode(pub_der).decode().rstrip("=")
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return pub_b64, sig_b64


async def test_bind_complete_rejected_without_attestation_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "attestation_enabled", True)
    challenge = "challenge-nonce"
    pub_b64, sig_b64 = _make_ecdsa_keypair_and_sig(challenge.encode())

    redis = AsyncMock()
    # 1st get: bind challenge present; 2nd get: attestation flag absent
    redis.get = AsyncMock(side_effect=[challenge.encode(), None])
    redis.delete = AsyncMock()

    device_repo = AsyncMock()
    device_repo.get_by_public_key = AsyncMock(return_value=None)
    svc = DeviceBindingService(device_repo, redis, AsyncMock())

    user = MagicMock()
    user.id = uuid.uuid4()

    with pytest.raises(DeviceBindingError, match="Device attestation required"):
        await svc.complete(user, "phone", pub_b64, sig_b64)


async def test_bind_complete_passes_when_attestation_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "attestation_enabled", True)
    challenge = "challenge-nonce-2"
    pub_b64, sig_b64 = _make_ecdsa_keypair_and_sig(challenge.encode())

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=[challenge.encode(), b"android"])
    redis.delete = AsyncMock()

    captured: dict[str, object] = {}

    async def _capture_create(device: object) -> object:
        captured["device"] = device
        return device

    device_repo = AsyncMock()
    device_repo.get_by_public_key = AsyncMock(return_value=None)
    device_repo.create = _capture_create  # type: ignore[assignment]

    svc = DeviceBindingService(device_repo, redis, AsyncMock())

    user = MagicMock()
    user.id = uuid.uuid4()

    await svc.complete(user, "phone", pub_b64, sig_b64)
    device = captured["device"]
    assert device.attestation_platform == "android"  # type: ignore[attr-defined]
    assert device.attested_at is not None  # type: ignore[attr-defined]
