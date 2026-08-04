import uuid
from datetime import UTC, datetime, timedelta

import jwt
import security.jwt as _sec_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from com.qode.qrew.v1.entry.core.config import settings


def _generate_keypair() -> tuple[str, str]:
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
_ALGORITHM = settings.scanner_jwt_algorithm

SCANNER_AUDIENCE = "qrew.scan"


def scanner_public_key() -> str:
    return _PUBLIC_KEY


def create_scanner_token(
    scanner_id: uuid.UUID,
    venue_id: uuid.UUID,
    event_id: uuid.UUID,
    date: str,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "scanner_id": str(scanner_id),
        "venue_id": str(venue_id),
        "event_id": str(event_id),
        "date": date,
        "type": "scanner",
        "aud": SCANNER_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=settings.scanner_token_expire_hours),
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=_ALGORITHM)


def decode_scanner_token(token: str) -> dict[str, object]:
    return _sec_jwt.decode_token(  # type: ignore[no-any-return]
        token,
        _PUBLIC_KEY,
        algorithms=[_ALGORITHM],
        audience=SCANNER_AUDIENCE,
    )


def decode_scanner_token_for_refresh(token: str) -> dict[str, object]:
    return jwt.decode(  # type: ignore[no-any-return]
        token,
        _PUBLIC_KEY,
        algorithms=[_ALGORITHM],
        options={"verify_exp": False, "verify_aud": False},
    )
