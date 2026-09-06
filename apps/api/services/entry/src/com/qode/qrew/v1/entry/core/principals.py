# verifies access and ticket qr tokens for the entry service
import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Final

import security.jwt as _sec_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import InvalidTokenError

from com.qode.qrew.v1.entry.core.config import settings

ALGORITHM: Final = "ES256"
ACCESS: Final = "access"
TICKET_QR: Final = "ticket_qr"
_PURPOSES: Final = (ACCESS, TICKET_QR)


@dataclass(frozen=True)
class _PurposeKeys:
    private_pem: str
    public_pem: str
    kid: str
    verifiers: dict[str, str] = field(default_factory=lambda: {})


# creates a throwaway signing key for local development
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


# derives the public key that matches a private key
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


# derives a stable identifier for a public key
def _kid_for(public_pem: str) -> str:
    return hashlib.sha256(public_pem.encode()).hexdigest()[:16]


# splits a concatenated string of public keys into individual keys
def _split_pems(raw: str) -> list[str]:
    parts = [chunk.strip() for chunk in raw.split("-----END PUBLIC KEY-----")]
    return [f"{p}\n-----END PUBLIC KEY-----\n" for p in parts if p.strip()]


# loads the signing and verification keys configured for a token purpose
def _load_purpose_keys(purpose: str) -> _PurposeKeys:
    raw: str = getattr(settings, f"{purpose}_jwt_private_key", "") or ""
    private_pem = raw.strip()
    if not private_pem:
        if not settings.debug:
            raise RuntimeError(
                f"{purpose.upper()}_JWT_PRIVATE_KEY is required in production"
            )
        private_pem, public_pem = _generate_ephemeral_keypair()
    else:
        public_pem = _derive_public_pem(private_pem)
    kid = _kid_for(public_pem)
    verifiers: dict[str, str] = {kid: public_pem}
    previous_raw: str = (
        getattr(settings, f"{purpose}_jwt_previous_public_keys", "") or ""
    )
    for previous_pem in _split_pems(previous_raw):
        verifiers[_kid_for(previous_pem)] = previous_pem
    return _PurposeKeys(
        private_pem=private_pem, public_pem=public_pem, kid=kid, verifiers=verifiers
    )


_KEYS: dict[str, _PurposeKeys] = {p: _load_purpose_keys(p) for p in _PURPOSES}


# verifies a token against the key its header names
def verify(purpose: str, token: str) -> dict[str, object]:
    keys = _KEYS[purpose]
    header = _sec_jwt.decode_unverified_header(token)
    kid = header.get("kid")
    public_pem = keys.verifiers.get(kid) if isinstance(kid, str) else None
    if public_pem is None:
        raise InvalidTokenError("Signing key unknown.")
    return _sec_jwt.decode_token(token, public_pem, algorithms=[ALGORITHM])  # type: ignore[no-any-return]


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    is_admin: bool = False


# verifies an access token and resolves the authenticated user
def verify_access_token(token: str) -> AuthenticatedUser:
    payload = verify(ACCESS, token)
    if payload.get("type") != "access":
        raise InvalidTokenError("Token type rejected.")
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError("Token subject missing.")
    return AuthenticatedUser(id=uuid.UUID(subject), is_admin=payload.get("adm") is True)


# returns the public keys that verify tokens of a purpose
def get_verifiers(purpose: str) -> dict[str, str]:
    return dict(_KEYS[purpose].verifiers)
