import hashlib
from enum import StrEnum
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    generate_private_key,
)

from com.qode.qrew.v1.sales.settings import settings

ALGORITHM = "ES256"


class Purpose(StrEnum):
    ACCESS = "access"
    QUEUE = "queue"


ACCESS = Purpose.ACCESS
QUEUE = Purpose.QUEUE


def _gen_ephemeral_pem() -> str:
    key = generate_private_key(SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _load_key(purpose: Purpose) -> tuple[str, str]:
    if purpose == Purpose.ACCESS:
        pem = settings.access_jwt_private_key
    else:
        pem = settings.queue_jwt_private_key
    if not pem:
        pem = _gen_ephemeral_pem()
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return pem, public_pem


def _key_id(public_pem: str) -> str:
    return hashlib.sha256(public_pem.encode()).hexdigest()[:16]


_KEY_CACHE: dict[Purpose, tuple[str, str]] = {}


def _get(purpose: Purpose) -> tuple[str, str]:
    if purpose not in _KEY_CACHE:
        _KEY_CACHE[purpose] = _load_key(purpose)
    return _KEY_CACHE[purpose]


def sign(purpose: Purpose, payload: dict[str, Any]) -> str:
    private_pem, public_pem = _get(purpose)
    return jwt.encode(
        payload,
        private_pem,
        algorithm=ALGORITHM,
        headers={"kid": _key_id(public_pem)},
    )


def verify(purpose: Purpose, token: str) -> dict[str, Any]:
    _, public_pem = _get(purpose)
    return jwt.decode(token, public_pem, algorithms=[ALGORITHM])  # type: ignore[return-value]


def verify_any(
    purposes: tuple[Purpose, ...], token: str
) -> tuple[Purpose, dict[str, Any]]:
    for purpose in purposes:
        try:
            return purpose, verify(purpose, token)
        except jwt.InvalidTokenError:
            continue
    raise jwt.InvalidTokenError("Token invalid for all attempted purposes")
