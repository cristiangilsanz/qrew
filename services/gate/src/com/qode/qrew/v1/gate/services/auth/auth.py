import uuid
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.gate.services.auth import jwt_keys
from com.qode.qrew.v1.gate.database import get_db
from com.qode.qrew.v1.gate.services.scanner.security import decode_scanner_token
from com.qode.qrew.v1.gate.models.identity import User
from com.qode.qrew.v1.gate.models.scanner import Scanner
from com.qode.qrew.v1.gate.repositories.scanner import ScannerRepository
from com.qode.qrew.v1.gate.repositories.user import UserRepository

logger = structlog.get_logger(__name__)

_bearer = HTTPBearer()

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Invalid or expired token", "field": None},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
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
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: AsyncSession = Depends(get_db),
) -> Scanner:
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
