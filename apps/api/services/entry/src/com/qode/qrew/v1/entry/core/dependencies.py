# provides the shared fastapi dependencies for the entry service
import uuid
from typing import Annotated

from db import create_redis_dependency
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.core.config import settings
from com.qode.qrew.v1.entry.core.database import get_db
from com.qode.qrew.v1.entry.core.errors import EventNotFoundError, NotEventMemberError
from com.qode.qrew.v1.entry.core.principals import (
    AuthenticatedUser,
    verify_access_token,
)
from com.qode.qrew.v1.entry.core.utils.jwt import decode_scanner_token
from com.qode.qrew.v1.entry.models.scanner import Scanner
from com.qode.qrew.v1.entry.repositories.scanner import ScannerRepository
from com.qode.qrew.v1.entry.services.application.audit import AuditService
from com.qode.qrew.v1.entry.services.application.catalog import (
    EventMembership,
    fetch_event_membership,
)
from com.qode.qrew.v1.entry.services.application.scanner import ScannerService

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)

get_redis = create_redis_dependency(settings.redis_url)

_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Token expired.", "field": None},
)


# resolves the authenticated user from the request headers or bearer token
async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> AuthenticatedUser:
    user_id_str = request.headers.get("x-authenticated-user-id")
    if user_id_str:
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            raise _CREDENTIALS_EXCEPTION from exc
        is_admin = request.headers.get("x-authenticated-user-is-admin") == "1"
        return AuthenticatedUser(id=user_id, is_admin=is_admin)
    if credentials is None:
        raise _CREDENTIALS_EXCEPTION
    try:
        return verify_access_token(credentials.credentials)
    except (ExpiredSignatureError, InvalidTokenError, ValueError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc


# rejects a request whose authenticated user is not an admin
async def get_admin_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin access required.", "field": None},
        )
    return current_user


# resolves the authenticated control device from its header or bearer token
async def get_scanner(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> Scanner:
    scanner_id_str = request.headers.get("x-authenticated-scanner-id")
    if scanner_id_str:
        try:
            scanner_id = uuid.UUID(scanner_id_str)
        except ValueError as exc:
            raise _CREDENTIALS_EXCEPTION from exc
    else:
        if credentials is None:
            raise _CREDENTIALS_EXCEPTION
        try:
            payload = decode_scanner_token(credentials.credentials)
        except (ExpiredSignatureError, InvalidTokenError) as exc:
            raise _CREDENTIALS_EXCEPTION from exc
        if payload.get("type") != "scanner":
            raise _CREDENTIALS_EXCEPTION
        scanner_id_raw = payload.get("scanner_id")
        if not isinstance(scanner_id_raw, str):
            raise _CREDENTIALS_EXCEPTION
        try:
            scanner_id = uuid.UUID(scanner_id_raw)
        except ValueError as exc:
            raise _CREDENTIALS_EXCEPTION from exc
    repo = ScannerRepository(db)
    scanner = await repo.get_by_id(scanner_id)
    if scanner is None or not scanner.is_active:
        raise _CREDENTIALS_EXCEPTION
    await repo.touch_last_used(scanner)
    return scanner


# builds a scanner service for a request
def get_scanner_service(db: AsyncSession = Depends(get_db)) -> ScannerService:
    return ScannerService(ScannerRepository(db), AuditService())


# reads from the local projection whether a user belongs to an event
async def event_membership(
    event_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> EventMembership:
    return await fetch_event_membership(db, event_id, user_id)


# rejects a request whose user does not belong to the event
async def require_event_member(
    event_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    membership = await event_membership(event_id, user_id, db)
    if not membership.event_exists:
        raise EventNotFoundError(event_id)
    if not membership.is_member:
        raise NotEventMemberError(user_id)
