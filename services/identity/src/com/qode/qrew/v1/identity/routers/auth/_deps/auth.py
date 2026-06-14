from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.database import get_db
from com.qode.qrew.v1.identity.redis import get_redis
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.device.device import DeviceRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.auth.breach_check import PasswordBreachChecker
from com.qode.qrew.v1.identity.services.auth.login import LoginService
from com.qode.qrew.v1.identity.services.auth.login_anomaly import LoginAnomalyService
from com.qode.qrew.v1.identity.services.auth.login_lockout import LoginLockoutService
from com.qode.qrew.v1.identity.services.auth.logout import LogoutService
from com.qode.qrew.v1.identity.services.auth.refresh import RefreshService
from com.qode.qrew.v1.identity.services.auth.session_cap import SessionCapEnforcer
from com.qode.qrew.v1.identity.services.infra.geoip import GeoIpService
from com.qode.qrew.v1.identity.services.infra.notification import NotificationDispatcher
from com.qode.qrew.v1.identity.services.session.session import SessionService

from .shared import get_geoip_service, get_notification_service


def get_login_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
    notifier: NotificationDispatcher = Depends(get_notification_service),
    geoip: GeoIpService = Depends(get_geoip_service),
) -> LoginService:
    """Build the login service."""
    session_repo = SessionRepository(db)
    anomaly = LoginAnomalyService(
        geoip=geoip,
        audit=AuditService(),
        session_repo=session_repo,
        notifier=notifier,
        redis=redis,
    )
    lockout = LoginLockoutService(redis, AuditService())
    session_cap = SessionCapEnforcer(session_repo, AuditService(), redis)
    breach_checker = PasswordBreachChecker(AuditService())
    return LoginService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        session_repo,
        anomaly,
        DeviceRepository(db),
        lockout,
        session_cap,
        breach_checker,
    )


def get_refresh_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> RefreshService:
    """Build the refresh service."""
    return RefreshService(
        UserRepository(db),
        redis,
        AuditService(),
        SessionRepository(db),
        DeviceRepository(db),
    )


def get_logout_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> LogoutService:
    """Build the logout service."""
    return LogoutService(redis, AuditService(), SessionRepository(db))


def get_session_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> SessionService:
    """Build the session service."""
    return SessionService(SessionRepository(db), redis)
