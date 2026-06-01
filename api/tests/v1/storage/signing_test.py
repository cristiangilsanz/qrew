import pytest

from com.qode.qrew.v1.service.core.storage.errors import (
    SignatureExpiredError,
    SignatureInvalidError,
)
from com.qode.qrew.v1.service.core.storage.signing import sign, verify


def test_roundtrip_passes_with_matching_inputs() -> None:
    expires_at, sig = sign(
        secret="s",
        method="PUT",
        key="user:u1/kyc/2026/06/01/abc",
        content_type="image/jpeg",
        ttl_seconds=60,
        now=1000,
    )
    verify(
        secret="s",
        method="PUT",
        key="user:u1/kyc/2026/06/01/abc",
        content_type="image/jpeg",
        expires_at=expires_at,
        signature=sig,
        now=1010,
    )


def test_verify_rejects_tampered_signature() -> None:
    expires_at, _sig = sign(
        secret="s",
        method="PUT",
        key="user:u1/kyc/2026/06/01/abc",
        content_type="image/jpeg",
        ttl_seconds=60,
        now=1000,
    )
    with pytest.raises(SignatureInvalidError):
        verify(
            secret="s",
            method="PUT",
            key="user:u1/kyc/2026/06/01/abc",
            content_type="image/jpeg",
            expires_at=expires_at,
            signature="deadbeef",
            now=1010,
        )


def test_verify_rejects_expired_signature() -> None:
    expires_at, sig = sign(
        secret="s",
        method="PUT",
        key="user:u1/kyc/2026/06/01/abc",
        content_type="image/jpeg",
        ttl_seconds=60,
        now=1000,
    )
    with pytest.raises(SignatureExpiredError):
        verify(
            secret="s",
            method="PUT",
            key="user:u1/kyc/2026/06/01/abc",
            content_type="image/jpeg",
            expires_at=expires_at,
            signature=sig,
            now=expires_at + 1,
        )


def test_verify_rejects_content_type_mismatch() -> None:
    expires_at, sig = sign(
        secret="s",
        method="PUT",
        key="user:u1/kyc/2026/06/01/abc",
        content_type="image/jpeg",
        ttl_seconds=60,
        now=1000,
    )
    with pytest.raises(SignatureInvalidError):
        verify(
            secret="s",
            method="PUT",
            key="user:u1/kyc/2026/06/01/abc",
            content_type="image/png",
            expires_at=expires_at,
            signature=sig,
            now=1010,
        )
