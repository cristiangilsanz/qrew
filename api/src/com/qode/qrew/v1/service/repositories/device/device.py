import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.device.device import Device


class DeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, device: Device) -> Device:
        self._session.add(device)
        await self._session.flush()
        await self._session.refresh(device)
        return device

    async def get_by_id(self, device_id: uuid.UUID) -> Device | None:
        result = await self._session.execute(
            select(Device).where(Device.id == device_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_by_user_id(self, user_id: uuid.UUID) -> list[Device]:
        result = await self._session.execute(
            select(Device)
            .where(Device.user_id == user_id)
            .order_by(Device.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_by_user_id(self, user_id: uuid.UUID) -> list[Device]:
        """Return non-revoked devices for the user, newest first."""
        result = await self._session.execute(
            select(Device)
            .where(Device.user_id == user_id, Device.revoked_at.is_(None))
            .order_by(Device.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_all_by_user_id(
        self, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> int:
        """Revoke every active device for a user."""
        stmt = select(Device).where(
            Device.user_id == user_id, Device.revoked_at.is_(None)
        )
        if exclude_id is not None:
            stmt = stmt.where(Device.id != exclude_id)
        result = await self._session.execute(stmt)
        devices = list(result.scalars().all())
        now = datetime.now(UTC)
        for device in devices:
            device.revoked_at = now
        await self._session.flush()
        return len(devices)

    async def get_by_public_key(self, public_key: bytes) -> Device | None:
        result = await self._session.execute(
            select(Device).where(Device.public_key == public_key).limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, device: Device) -> Device:
        await self._session.flush()
        await self._session.refresh(device)
        return device

    async def delete_by_id(self, device_id: uuid.UUID) -> None:
        await self._session.execute(delete(Device).where(Device.id == device_id))
        await self._session.flush()
