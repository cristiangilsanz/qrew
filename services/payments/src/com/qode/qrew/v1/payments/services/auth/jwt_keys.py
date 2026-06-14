import hashlib
from dataclasses import dataclass, field
from typing import Final

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import InvalidTokenError

from com.qode.qrew.v1.payments.settings import settings

ALGORITHM: Final = "ES256"

ACCESS: Final = "access"
PURPOSES: Final = (ACCESS,)


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


def _settings_attr(purpose: str) -> str:
    return f"{purpose}_jwt_private_key"


def _previous_settings_attr(purpose: str) -> str:
    return f"{purpose}_jwt_previous_public_keys"


def _load_purpose_keys(purpose: str) -> _PurposeKeys:
    raw: str = getattr(settings, _settings_attr(purpose), "") or ""
    private_pem = raw.strip()
    if not private_pem:
        if not settings.debug:
            raise RuntimeError(
                f"{_settings_attr(purpose).upper()} is required when debug=False"
            )
        private_pem, public_pem = _generate_ephemeral_keypair()
    else:
        public_pem = _derive_public_pem(private_pem)
    kid = _kid_for(public_pem)

    verifiers: dict[str, str] = {kid: public_pem}
    previous_raw: str = getattr(settings, _previous_settings_attr(purpose), "") or ""
    for previous_pem in _split_pems(previous_raw):
        verifiers[_kid_for(previous_pem)] = previous_pem

    return _PurposeKeys(
        private_pem=private_pem,
        public_pem=public_pem,
        kid=kid,
        verifiers=verifiers,
    )


_KEYS: dict[str, _PurposeKeys] = {p: _load_purpose_keys(p) for p in PURPOSES}


def verify(purpose: str, token: str) -> dict[str, object]:
    keys = _KEYS[purpose]
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    public_pem = keys.verifiers.get(kid) if isinstance(kid, str) else None
    if public_pem is None:
        raise InvalidTokenError("Unknown signing key")
    return jwt.decode(  # type: ignore[no-any-return]
        token,
        public_pem,
        algorithms=[ALGORITHM],
    )
