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
from com.qode.qrew.v1.entry.core.principals import verify_access_token
from com.qode.qrew.v1.entry.core.utils.jwt import decode_scanner_token
from com.qode.qrew.v1.entry.models.projections import User
from com.qode.qrew.v1.entry.models.scanner import Scanner
from com.qode.qrew.v1.entry.repositories.projections import (
    EventRepository,
    OrganisationMemberRepository,
    UserRepository,
)
from com.qode.qrew.v1.entry.repositories.scanner import ScannerRepository
from com.qode.qrew.v1.entry.services.application.audit import AuditService
from com.qode.qrew.v1.entry.services.application.scanner import ScannerService

limiter = Limiter(key_func=get_remote_address, enabled=settings.ratelimit_enabled)

get_redis = create_redis_dependency(settings.redis_url)

_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Invalid or expired token", "field": None},
)


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id_str = request.headers.get("x-authenticated-user-id")
    if user_id_str:
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            raise _CREDENTIALS_EXCEPTION from exc
    else:
        if credentials is None:
            raise _CREDENTIALS_EXCEPTION
        try:
            user_id = verify_access_token(credentials.credentials)
        except (ExpiredSignatureError, InvalidTokenError, ValueError) as exc:
            raise _CREDENTIALS_EXCEPTION from exc
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin access required", "field": None},
        )
    return current_user


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


def get_scanner_service(db: AsyncSession = Depends(get_db)) -> ScannerService:
    return ScannerService(ScannerRepository(db), AuditService())


async def require_event_member(
    db: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    event = await EventRepository(db).get_by_id(event_id)
    if event is None:
        raise EventNotFoundError(event_id)
    member = await OrganisationMemberRepository(db).get(event.organisation_id, user_id)
    if member is None:
        raise NotEventMemberError(user_id)
