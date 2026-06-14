from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.services.device.attestation import build_attestation_verifier
from com.qode.qrew.v1.identity.database import get_db
from com.qode.qrew.v1.identity.redis import get_redis
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.device.device import DeviceRepository
from com.qode.qrew.v1.identity.repositories.device.fingerprint import (
    DeviceFingerprintRepository,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.device.device import DeviceService
from com.qode.qrew.v1.identity.services.device.device_attestation import (
    DeviceAttestationService,
)
from com.qode.qrew.v1.identity.services.device.device_binding import DeviceBindingService
from com.qode.qrew.v1.identity.services.device.fingerprint import FingerprintService


def get_fingerprint_service(
    db: AsyncSession = Depends(get_db),
) -> FingerprintService:
    """Build the fingerprint service."""
    return FingerprintService(DeviceFingerprintRepository(db), AuditService())


def get_device_binding_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceBindingService:
    """Build the device binding service."""
    return DeviceBindingService(DeviceRepository(db), redis, AuditService())


def get_device_attestation_service(
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceAttestationService:
    """Build the device attestation service."""
    return DeviceAttestationService(build_attestation_verifier(), redis, AuditService())


def get_device_service(
    db: AsyncSession = Depends(get_db),
    redis: Annotated[aioredis.Redis, Depends(get_redis)] = ...,  # type: ignore[type-arg, assignment]
) -> DeviceService:
    """Build the device management service."""
    return DeviceService(
        DeviceRepository(db),
        SessionRepository(db),
        redis,
        AuditService(),
    )
