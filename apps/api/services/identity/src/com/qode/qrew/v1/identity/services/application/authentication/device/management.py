import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.models.device import Device
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.device import DeviceRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_BLACKLIST_JTI_PREFIX = "blacklist:jti:"
_JTI_TTL_SECONDS = settings.refresh_token_expire_days * 86400


async def _publish_device_revoked(
    device_id: uuid.UUID, user_id: uuid.UUID, revoked_at: datetime | None
) -> None:
    """Announces a revoked device so the ticketing projection stops trusting it."""
    try:
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-not-found]
        from messaging.publisher import publish as nats_publish  # type: ignore[import-not-found]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="device",
            aggregate_id=str(device_id),
            actor_id=str(user_id),
            data={
                "device_id": str(device_id),
                "user_id": str(user_id),
                "revoked_at": (revoked_at or datetime.now(UTC)).isoformat(),
            },
        )
        await nats_publish("identity.device.revoked.v1", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed", subject="identity.device.revoked.v1", error=repr(exc)
        )


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

        device.revoked_at = datetime.now(UTC)
        await self._device_repo.save(device)

        await self._kill_device_sessions(device.id)

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

        await _publish_device_revoked(device_id, user.id, device.revoked_at)

    async def revoke_all_devices(
        self,
        user: User,
        calling_device_id: uuid.UUID | None = None,
    ) -> int:
        """Revokes all devices for the user except the one currently in use."""
        revoked_ids = await self._device_repo.revoke_all_by_user_id(
            user.id, exclude_id=calling_device_id
        )
        revoked_count = len(revoked_ids)

        await self._kill_all_sessions(user.id)

        now = datetime.now(UTC)
        for revoked_id in revoked_ids:
            await _publish_device_revoked(revoked_id, user.id, now)

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

    async def _kill_device_sessions(self, device_id: uuid.UUID) -> None:
        """Removes sessions linked to a specific device and blacklists their tokens."""
        jtis = await self._session_repo.delete_by_device_id(device_id)
        for jti in jtis:
            await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, _JTI_TTL_SECONDS, "1")

    async def _kill_all_sessions(self, user_id: uuid.UUID) -> None:
        """Removes all active sessions for a user and invalidates their tokens."""
        jtis = await self._session_repo.delete_all_by_user_id(user_id)
        for jti in jtis:
            await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, _JTI_TTL_SECONDS, "1")
