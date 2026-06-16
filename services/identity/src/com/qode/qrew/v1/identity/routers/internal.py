from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from com.qode.qrew.v1.identity.services.auth import jwt_keys
from com.qode.qrew.v1.identity.core.config import settings

router = APIRouter(prefix="/internal", include_in_schema=False)

_ALLOWED_PURPOSES = set(jwt_keys.PURPOSES)


def _require_internal_key(request: Request) -> None:
    key = request.headers.get("X-Internal-Key", "")
    if not key or key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


class _SignRequest(BaseModel):
    purpose: str
    claims: dict[str, object]
    ttl_seconds: int = 300


class _SignResponse(BaseModel):
    token: str


@router.post("/_internal/jwt/sign", response_model=_SignResponse)
async def sign_jwt(body: _SignRequest, request: Request) -> _SignResponse:
    """Issues a signed token for a given purpose on behalf of a sibling service."""
    _require_internal_key(request)
    if body.purpose not in _ALLOWED_PURPOSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "invalid_purpose", "message": f"Unknown purpose: {body.purpose}"},
        )
    claims = dict(body.claims)
    now = datetime.now(UTC)
    claims.setdefault("iat", int(now.timestamp()))
    claims.setdefault("exp", int((now + timedelta(seconds=body.ttl_seconds)).timestamp()))
    claims.setdefault("purpose", body.purpose)
    token = jwt_keys.sign(body.purpose, claims)
    return _SignResponse(token=token)
