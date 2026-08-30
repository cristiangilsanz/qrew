# signs and verifies access and queue tokens for the sales service
import hashlib
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Optional

import jwt
import security.jwt as _sec_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from com.qode.qrew.v1.sales.core.config import settings

ALGORITHM = "ES256"

_bearer = HTTPBearer(auto_error=False)


class Purpose(StrEnum):
    ACCESS = "access"
    QUEUE = "queue"


ACCESS = Purpose.ACCESS
QUEUE = Purpose.QUEUE


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID


# creates a throwaway signing key for local development
def _gen_ephemeral_pem() -> str:
    key = generate_private_key(SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


# loads the configured signing key for a token purpose and derives its public key
def _load_key(purpose: Purpose) -> tuple[str, str]:
    if purpose == Purpose.ACCESS:
        pem = settings.access_jwt_private_key
    else:
        pem = settings.queue_jwt_private_key
    if not pem:
        pem = _gen_ephemeral_pem()
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return pem, public_pem


_KEY_CACHE: dict[Purpose, tuple[str, str]] = {}


# returns the cached key pair for a token purpose loading it once
def _get(purpose: Purpose) -> tuple[str, str]:
    if purpose not in _KEY_CACHE:
        _KEY_CACHE[purpose] = _load_key(purpose)
    return _KEY_CACHE[purpose]


# signs a payload with the key configured for a token purpose
def sign(purpose: Purpose, payload: dict[str, Any]) -> str:
    private_pem, public_pem = _get(purpose)
    kid = hashlib.sha256(public_pem.encode()).hexdigest()[:16]
    return jwt.encode(payload, private_pem, algorithm=ALGORITHM, headers={"kid": kid})


# verifies a token against the key configured for a token purpose
def verify(purpose: Purpose, token: str) -> dict[str, Any]:
    _, public_pem = _get(purpose)
    return _sec_jwt.decode_token(token, public_pem, algorithms=[ALGORITHM])  # type: ignore[return-value]


# verifies a token against whichever of the given purposes matches
def verify_any(purposes: tuple[Purpose, ...], token: str) -> tuple[Purpose, dict[str, Any]]:
    for purpose in purposes:
        try:
            return purpose, verify(purpose, token)
        except jwt.InvalidTokenError:
            continue
    raise jwt.InvalidTokenError("Token rejected.")


# resolves the authenticated user from the request headers or bearer token
def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthenticatedUser:
    user_id_str = request.headers.get("x-authenticated-user-id")
    if user_id_str:
        try:
            return AuthenticatedUser(id=uuid.UUID(user_id_str))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Token expired."},
            ) from exc
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Token expired."},
        )
    token = credentials.credentials
    try:
        payload = verify(ACCESS, token)
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise ValueError("Token subject missing.")
        return AuthenticatedUser(id=uuid.UUID(sub))
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Token expired."},
        ) from exc
