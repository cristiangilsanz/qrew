"""RS256 signing helpers for scanner credentials.

Scanner JWTs are asymmetric: the private key signs server-side, scanner
devices verify offline with the public key. Keys come from settings; if
unset (dev/test), an ephemeral RSA-2048 key pair is generated at import.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from com.qode.qrew.v1.service.settings import settings


def _generate_keypair() -> tuple[str, str]:
    """Generate a fresh RSA-2048 PEM key pair (PKCS8 / SubjectPublicKeyInfo)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _resolve_keys() -> tuple[str, str]:
    if settings.scanner_jwt_private_key and settings.scanner_jwt_public_key:
        return settings.scanner_jwt_private_key, settings.scanner_jwt_public_key
    return _generate_keypair()


_PRIVATE_KEY, _PUBLIC_KEY = _resolve_keys()


def scanner_public_key() -> str:
    """Return the PEM-encoded public key used to verify scanner JWTs."""
    return _PUBLIC_KEY


def create_scanner_token(
    scanner_id: uuid.UUID,
    venue_id: uuid.UUID,
    event_id: uuid.UUID,
    date: str,
) -> str:
    """Return a short-lived RS256-signed JWT for a scanner device."""
    now = datetime.now(UTC)
    payload = {
        "scanner_id": str(scanner_id),
        "venue_id": str(venue_id),
        "event_id": str(event_id),
        "date": date,
        "type": "scanner",
        "iat": now,
        "exp": now + timedelta(hours=settings.scanner_token_expire_hours),
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")


def decode_scanner_token(token: str) -> dict[str, object]:
    """Decode and validate a scanner JWT; raises jwt errors on failure."""
    return jwt.decode(token, _PUBLIC_KEY, algorithms=["RS256"])  # type: ignore[no-any-return]
