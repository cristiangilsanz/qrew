import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.outbox import publish_via_outbox
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.models.device.device import Device
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.service.repositories.device.device import DeviceRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket import transition_ticket
from com.qode.qrew.v1.service.settings import settings

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
        session: AsyncSession | None = None,
    ) -> None:
        self._device_repo = device_repo
        self._session_repo = session_repo
        self._redis = redis
        self._audit = audit
        self._session = session

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
            raise DeviceError(
                "Cannot revoke the device you are currently using.", field=None
            )

        device.revoked_at = datetime.now(UTC)
        await self._device_repo.save(device)

        frozen_count = await self._freeze_bound_tickets(user.id, device_id)

        await self._kill_all_sessions(user.id)

        await logger.ainfo(
            "device_revoked", user_id=str(user.id), device_id=str(device_id)
        )
        try:
            await self._audit.record(
                action=AuditAction.DEVICE_REVOKE,
                actor_id=user.id,
                entity_type="device",
                entity_id=str(device_id),
                payload={"reason": "user_initiated", "frozen_tickets": frozen_count},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.DEVICE_REVOKE
            )

    async def revoke_all_devices(
        self,
        user: User,
        calling_device_id: uuid.UUID | None = None,
    ) -> int:
        """Revoke every device except the calling one; returns count revoked."""
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
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.DEVICE_REVOKE_ALL
            )

        return revoked_count

    async def _freeze_bound_tickets(
        self, user_id: uuid.UUID, device_id: uuid.UUID
    ) -> int:
        """Transition `issued` tickets bound to this device to `frozen`.

        Returns the count actually frozen. No-op when the service was built
        without a DB session (legacy callers without ticket context).
        """
        if self._session is None:
            return 0
        result = await self._session.execute(
            select(Ticket).where(
                Ticket.owner_user_id == user_id,
                Ticket.bound_device_id == device_id,
                Ticket.state == TicketState.issued,
            )
        )
        affected = list(result.scalars().all())
        if not affected:
            return 0
        for ticket in affected:
            await transition_ticket(
                self._session,
                ticket_id=ticket.id,
                to_state=TicketState.frozen,
                reason="device_revoked",
                actor_id=user_id,
                audit=self._audit,
            )
            try:
                await self._audit.record(
                    action=AuditAction.TICKET_FROZEN_DEVICE_REVOKE,
                    actor_id=user_id,
                    entity_type="ticket",
                    entity_id=str(ticket.id),
                    payload={"device_id": str(device_id)},
                )
            except Exception:
                await logger.awarning(
                    "audit_write_failed",
                    action=AuditAction.TICKET_FROZEN_DEVICE_REVOKE,
                )
        try:
            await publish_via_outbox(
                self._session,
                aggregate_type="device",
                aggregate_id=str(device_id),
                job_name="notifications.tickets_frozen_device_revoke",
                payload={
                    "user_id": str(user_id),
                    "device_id": str(device_id),
                    "ticket_count": len(affected),
                },
            )
        except Exception:
            await logger.awarning("outbox_publish_failed")
        return len(affected)

    async def _kill_all_sessions(self, user_id: uuid.UUID) -> None:
        """Delete all sessions for the user and blacklist their JTIs in Redis."""
        jtis = await self._session_repo.delete_all_by_user_id(user_id)
        for jti in jtis:
            await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, _JTI_TTL_SECONDS, "1")
