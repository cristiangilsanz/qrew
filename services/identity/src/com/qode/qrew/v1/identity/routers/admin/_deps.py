from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.dependencies import get_redis
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.device.fingerprint import (
    DeviceFingerprintRepository,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.auth.login_lockout import LoginLockoutService
from com.qode.qrew.v1.identity.services.device.fingerprint import FingerprintService
from com.qode.qrew.v1.identity.services.notification import (
    NotificationDispatcher,
    build_notification_dispatcher,
)
from com.qode.qrew.v1.identity.services.kyc.kyc_review import KycReviewService


def _get_notification_service() -> NotificationDispatcher:
    """Build the notification dispatcher."""
    return build_notification_dispatcher()


def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    """Build the user repository."""
    return UserRepository(db)


def get_fingerprint_service(
    db: AsyncSession = Depends(get_db),
) -> FingerprintService:
    """Build the fingerprint service."""
    return FingerprintService(DeviceFingerprintRepository(db), AuditService())


def get_kyc_review_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(_get_notification_service),
) -> KycReviewService:
    """Build the KYC review service."""
    return KycReviewService(UserRepository(db), notifier, AuditService())


def get_login_lockout_service(
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LoginLockoutService:
    """Build the login lockout service."""
    return LoginLockoutService(redis, AuditService())
