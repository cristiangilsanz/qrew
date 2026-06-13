"""JWT authentication for the catalog service.

Auth validates an Access JWT and returns an AuthenticatedUser.
No DB lookup is needed — the user id comes straight from the token.
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from com.qode.qrew.v1.catalog.core.api.errors import credentials_exception
from com.qode.qrew.v1.catalog.core.auth import jwt_keys

_bearer = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthenticatedUser:
    try:
        payload = jwt_keys.verify(jwt_keys.ACCESS, credentials.credentials)
    except Exception:
        raise credentials_exception()
    if payload.get("type") != "access":
        raise credentials_exception()
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError):
        raise credentials_exception()
    return AuthenticatedUser(id=user_id)
