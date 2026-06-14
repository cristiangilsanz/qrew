import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from com.qode.qrew.v1.ticketing.services.auth.jwt_keys import ACCESS, verify

_bearer = HTTPBearer()


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    device_id: uuid.UUID | None = None
    last_asserted_at: datetime | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthenticatedUser:
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
        last_asserted_at: datetime | None = None
        if isinstance(raw_asserted, (int, float)):
            last_asserted_at = datetime.fromtimestamp(raw_asserted, tz=UTC)
        elif isinstance(raw_asserted, datetime):
            last_asserted_at = raw_asserted
        return AuthenticatedUser(id=user_id, device_id=device_id, last_asserted_at=last_asserted_at)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token"},
        ) from exc
