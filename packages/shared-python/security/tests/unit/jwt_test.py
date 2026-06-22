from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from security.jwt import decode_token, decode_unverified_header

_private_key = ec.generate_private_key(ec.SECP256R1())
_public_key = _private_key.public_key()
PRIVATE_PEM = _private_key.private_bytes(
    Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
).decode()
PUBLIC_PEM = _public_key.public_bytes(
    Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
).decode()

_other_key = ec.generate_private_key(ec.SECP256R1())
OTHER_PRIVATE_PEM = _other_key.private_bytes(
    Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
).decode()
OTHER_PUBLIC_PEM = (
    _other_key.public_key()
    .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    .decode()
)


def _make_token(payload: dict, private_pem: str = PRIVATE_PEM) -> str:
    return pyjwt.encode(payload, private_pem, algorithm="ES256")


class TestDecodeUnverifiedHeader:
    def test_returns_dict_with_alg(self) -> None:
        token = _make_token(
            {"sub": "u1", "exp": datetime.now(UTC) + timedelta(hours=1)}
        )
        header = decode_unverified_header(token)
        assert isinstance(header, dict)
        assert "alg" in header

    def test_alg_is_es256(self) -> None:
        token = _make_token(
            {"sub": "u1", "exp": datetime.now(UTC) + timedelta(hours=1)}
        )
        header = decode_unverified_header(token)
        assert header["alg"] == "ES256"


class TestDecodeToken:
    def test_valid_token_returns_claims(self) -> None:
        payload = {"sub": "user-123", "exp": datetime.now(UTC) + timedelta(hours=1)}
        token = _make_token(payload)
        claims = decode_token(token, PUBLIC_PEM)
        assert claims["sub"] == "user-123"

    def test_expired_token_raises(self) -> None:
        payload = {"sub": "u1", "exp": datetime.now(UTC) - timedelta(seconds=1)}
        token = _make_token(payload)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(token, PUBLIC_PEM)

    def test_wrong_key_raises(self) -> None:
        payload = {"sub": "u1", "exp": datetime.now(UTC) + timedelta(hours=1)}
        token = _make_token(payload)
        with pytest.raises((pyjwt.InvalidSignatureError, pyjwt.DecodeError)):
            decode_token(token, OTHER_PUBLIC_PEM)

    def test_correct_audience_succeeds(self) -> None:
        payload = {
            "sub": "u1",
            "aud": "my-app",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = _make_token(payload)
        claims = decode_token(token, PUBLIC_PEM, audience="my-app")
        assert claims["sub"] == "u1"

    def test_wrong_audience_raises(self) -> None:
        payload = {
            "sub": "u1",
            "aud": "my-app",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = _make_token(payload)
        with pytest.raises(pyjwt.InvalidAudienceError):
            decode_token(token, PUBLIC_PEM, audience="wrong-app")
