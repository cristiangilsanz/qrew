from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.dependencies import get_redis
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.services.account.account_deletion import (
    AccountDeletionService,
)
from com.qode.qrew.v1.identity.services.account.email_change import EmailChangeService
from com.qode.qrew.v1.identity.services.account.password_change import (
    PasswordChangeService,
)
from com.qode.qrew.v1.identity.services.account.phone_change import PhoneChangeService
from com.qode.qrew.v1.identity.services.account.recovery import RecoveryService
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.notification import NotificationDispatcher
from com.qode.qrew.v1.identity.services.kyc.ocr import OcrService

from .shared import get_notification_service, get_ocr_service


def get_email_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> EmailChangeService:
    """Constructs and returns a ready-to-use handler for updating a user's email address."""
    return EmailChangeService(UserRepository(db), notifier, AuditService())


def get_phone_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> PhoneChangeService:
    """Constructs and returns a ready-to-use handler for updating a user's phone number."""
    return PhoneChangeService(UserRepository(db), notifier, AuditService())


def get_password_change_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasswordChangeService:
    """Constructs and returns a ready-to-use handler for updating a user's password."""
    return PasswordChangeService(
        UserRepository(db),
        SessionRepository(db),
        redis,
        AuditService(),
    )


def get_account_deletion_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> AccountDeletionService:
    """Constructs and returns a ready-to-use handler for permanently removing a user account."""
    return AccountDeletionService(
        UserRepository(db),
        SessionRepository(db),
        PasskeyCredentialRepository(db),
        redis,
        AuditService(),
    )


def get_recovery_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
    notifier: NotificationDispatcher = Depends(get_notification_service),
    ocr: OcrService = Depends(get_ocr_service),
) -> RecoveryService:
    """Constructs and returns a ready-to-use handler for recovering access to a locked account."""
    return RecoveryService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        SessionRepository(db),
        redis,
        notifier,
        AuditService(),
        ocr,
    )
