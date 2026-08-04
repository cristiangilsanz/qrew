import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Final, Optional

import jwt
import security.jwt as _sec_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from com.qode.qrew.v1.ticketing.core.config import settings

ALGORITHM: Final = "ES256"
ACCESS: Final = "access"
TICKET_QR: Final = "ticket_qr"  # noqa: S105
_PURPOSES: Final = (ACCESS, TICKET_QR)

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    device_id: uuid.UUID | None = None
    last_asserted_at: object = None


@dataclass(frozen=True)
class _PurposeKeys:
    private_pem: str
    public_pem: str
    kid: str
    verifiers: dict[str, str] = field(default_factory=lambda: {})


def _generate_ephemeral_keypair() -> tuple[str, str]:
    private = ec.generate_private_key(ec.SECP256R1())
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _derive_public_pem(private_pem: str) -> str:
    key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    return (
        key.public_key()
        .public_bytes(  # type: ignore[union-attr]
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


def _kid_for(public_pem: str) -> str:
    return hashlib.sha256(public_pem.encode()).hexdigest()[:16]


def _split_pems(raw: str) -> list[str]:
    parts = [chunk.strip() for chunk in raw.split("-----END PUBLIC KEY-----")]
    return [f"{p}\n-----END PUBLIC KEY-----\n" for p in parts if p.strip()]


def _load_purpose_keys(purpose: str) -> _PurposeKeys:
    raw: str = getattr(settings, f"{purpose}_jwt_private_key", "") or ""
    private_pem = raw.strip()
    if not private_pem:
        if not settings.debug:
            raise RuntimeError(f"{purpose.upper()}_JWT_PRIVATE_KEY is required in production")
        private_pem, public_pem = _generate_ephemeral_keypair()
    else:
        public_pem = _derive_public_pem(private_pem)
    kid = _kid_for(public_pem)
    verifiers: dict[str, str] = {kid: public_pem}
    previous_raw: str = getattr(settings, f"{purpose}_jwt_previous_public_keys", "") or ""
    for previous_pem in _split_pems(previous_raw):
        verifiers[_kid_for(previous_pem)] = previous_pem
    return _PurposeKeys(
        private_pem=private_pem, public_pem=public_pem, kid=kid, verifiers=verifiers
    )


_KEYS: dict[str, _PurposeKeys] = {p: _load_purpose_keys(p) for p in _PURPOSES}


def kid_for(purpose: str) -> str:
    return _KEYS[purpose].kid


def sign(purpose: str, claims: dict[str, object]) -> str:
    keys = _KEYS[purpose]
    return jwt.encode(claims, keys.private_pem, algorithm=ALGORITHM, headers={"kid": keys.kid})


def verify(purpose: str, token: str) -> dict[str, object]:
    keys = _KEYS[purpose]
    header = _sec_jwt.decode_unverified_header(token)
    kid = header.get("kid")
    public_pem = keys.verifiers.get(kid) if isinstance(kid, str) else None
    if public_pem is None:
        raise InvalidTokenError("Unknown signing key")
    return _sec_jwt.decode_token(token, public_pem, algorithms=[ALGORITHM])  # type: ignore[no-any-return]


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthenticatedUser:
    from datetime import UTC, datetime

    user_id_str = request.headers.get("x-authenticated-user-id")
    if user_id_str:
        try:
            return AuthenticatedUser(id=uuid.UUID(user_id_str))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid or expired token"},
            ) from exc
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token"},
        )
    token = credentials.credentials
    try:
        payload = verify(ACCESS, token)
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise ValueError("missing sub")
        user_id = uuid.UUID(sub)
        raw_device = payload.get("device_id")
        device_id = uuid.UUID(raw_device) if isinstance(raw_device, str) else None
        raw_asserted = payload.get("last_asserted_at")
        last_asserted_at = None
        if isinstance(raw_asserted, (int, float)):
            last_asserted_at = datetime.fromtimestamp(raw_asserted, tz=UTC)
        return AuthenticatedUser(id=user_id, device_id=device_id, last_asserted_at=last_asserted_at)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token"},
        ) from exc
