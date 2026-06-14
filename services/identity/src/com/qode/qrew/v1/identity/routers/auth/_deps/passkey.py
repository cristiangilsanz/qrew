from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.database import get_db
from com.qode.qrew.v1.identity.redis import get_redis
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.passkey import (
    PasskeyAuthenticationService,
    PasskeyManagementService,
    PasskeyReassertionService,
    PasskeyRegistrationService,
)


def get_passkey_registration_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyRegistrationService:
    """Build the passkey registration service."""
    return PasskeyRegistrationService(PasskeyCredentialRepository(db), redis, AuditService())


def get_passkey_authentication_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyAuthenticationService:
    """Build the passkey authentication service."""
    return PasskeyAuthenticationService(
        PasskeyCredentialRepository(db),
        redis,
        UserRepository(db),
        AuditService(),
        SessionRepository(db),
    )


def get_passkey_reassertion_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasskeyReassertionService:
    """Build the passkey re-assertion service."""
    return PasskeyReassertionService(
        PasskeyCredentialRepository(db),
        redis,
        AuditService(),
        SessionRepository(db),
    )


def get_passkey_management_service(
    db: AsyncSession = Depends(get_db),
) -> PasskeyManagementService:
    """Build the passkey management service."""
    return PasskeyManagementService(PasskeyCredentialRepository(db), AuditService())
