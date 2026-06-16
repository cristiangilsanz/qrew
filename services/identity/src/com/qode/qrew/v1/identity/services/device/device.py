import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.models.auth.user import User
from com.qode.qrew.v1.identity.models.device.device import Device
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.device.device import DeviceRepository
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_BLACKLIST_JTI_PREFIX = "blacklist:jti:"
_JTI_TTL_SECONDS = settings.refresh_token_expire_days * 86400


class DeviceError(DomainError):
    """Raised when a device management operation cannot be completed."""


class DeviceService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        session_repo: SessionRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
        session: object | None = None,  # kept for backwards compat, unused
    ) -> None:
        self._device_repo = device_repo
        self._session_repo = session_repo
        self._redis = redis
        self._audit = audit

    async def list_devices(self, user: User) -> list[Device]:
        """Return all non-revoked devices for the user."""
        return await self._device_repo.get_active_by_user_id(user.id)

    async def revoke_device(
        self,
        user: User,
        device_id: uuid.UUID,
        calling_device_id: uuid.UUID | None = None,
    ) -> None:
        """Mark a device as revoked and cascade-kill all user sessions."""
        device = await self._device_repo.get_by_id(device_id)
        if device is None or device.user_id != user.id:
            raise DeviceError("Device not found.", field=None)
        if device.revoked_at is not None:
            raise DeviceError("Device is already revoked.", field=None)
        if calling_device_id is not None and calling_device_id == device_id:
            raise DeviceError("Cannot revoke the device you are currently using.", field=None)

        device.revoked_at = datetime.now(UTC)
        await self._device_repo.save(device)

        await self._kill_all_sessions(user.id)

        await logger.ainfo("device_revoked", user_id=str(user.id), device_id=str(device_id))
        try:
            await self._audit.record(
                action=AuditAction.DEVICE_REVOKE,
                actor_id=user.id,
                entity_type="device",
                entity_id=str(device_id),
                payload={"reason": "user_initiated"},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.DEVICE_REVOKE, error=repr(exc)
            )

    async def revoke_all_devices(
        self,
        user: User,
        calling_device_id: uuid.UUID | None = None,
    ) -> int:
        """Revokes all devices for the user except the one currently in use."""
        revoked_count = await self._device_repo.revoke_all_by_user_id(
            user.id, exclude_id=calling_device_id
        )

        await self._kill_all_sessions(user.id)

        await logger.ainfo(
            "devices_revoke_all",
            user_id=str(user.id),
            revoked_count=revoked_count,
        )
        try:
            await self._audit.record(
                action=AuditAction.DEVICE_REVOKE_ALL,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                payload={"reason": "user_initiated", "revoked_count": revoked_count},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.DEVICE_REVOKE_ALL, error=repr(exc)
            )

        return revoked_count

    async def _kill_all_sessions(self, user_id: uuid.UUID) -> None:
        """Removes all active sessions for a user and invalidates their tokens."""
        jtis = await self._session_repo.delete_all_by_user_id(user_id)
        for jti in jtis:
            await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, _JTI_TTL_SECONDS, "1")
