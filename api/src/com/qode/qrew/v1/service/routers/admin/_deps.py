from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.redis import get_redis
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.repositories.device.fingerprint import (
    DeviceFingerprintRepository,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.auth.login_lockout import LoginLockoutService
from com.qode.qrew.v1.service.services.device.fingerprint import FingerprintService
from com.qode.qrew.v1.service.services.infra.notification import (
    NotificationDispatcher,
    build_notification_dispatcher,
)
from com.qode.qrew.v1.service.services.kyc.kyc_review import KycReviewService


def _get_notification_service() -> NotificationDispatcher:
    """Build the notification dispatcher."""
    return build_notification_dispatcher()


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
