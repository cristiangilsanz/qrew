import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from com.qode.qrew.v1.sales.services.auth.jwt_keys import ACCESS, verify

_bearer = HTTPBearer()


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        payload = verify(ACCESS, token)
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise ValueError("missing sub")
        return AuthenticatedUser(id=uuid.UUID(sub))
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token"},
        ) from exc
