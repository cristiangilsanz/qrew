from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.redis import get_redis
from com.qode.qrew.v1.service.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.service.services.account.account_deletion import (
    AccountDeletionService,
)
from com.qode.qrew.v1.service.services.account.email_change import EmailChangeService
from com.qode.qrew.v1.service.services.account.password_change import (
    PasswordChangeService,
)
from com.qode.qrew.v1.service.services.account.phone_change import PhoneChangeService
from com.qode.qrew.v1.service.services.account.recovery import RecoveryService
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.infra.notification import NotificationDispatcher
from com.qode.qrew.v1.service.services.kyc.ocr import OcrService

from .shared import get_notification_service, get_ocr_service


def get_email_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> EmailChangeService:
    """Build the email change service."""
    return EmailChangeService(UserRepository(db), notifier, AuditService())


def get_phone_change_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> PhoneChangeService:
    """Build the phone change service."""
    return PhoneChangeService(UserRepository(db), notifier, AuditService())


def get_password_change_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> PasswordChangeService:
    """Build the password change service."""
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
    """Build the account deletion service."""
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
    """Build the account recovery service."""
    return RecoveryService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        SessionRepository(db),
        redis,
        notifier,
        AuditService(),
        ocr,
    )
