import uuid
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError

from com.qode.qrew.v1.payments.core.auth import jwt_keys

logger = structlog.get_logger(__name__)

_bearer = HTTPBearer()

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Invalid or expired token", "field": None},
)


class AuthenticatedUser:
    def __init__(self, user_id: uuid.UUID) -> None:
        self.id = user_id


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> AuthenticatedUser:
    try:
        payload = jwt_keys.verify(jwt_keys.ACCESS, credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXCEPTION

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    return AuthenticatedUser(user_id)
