# reads and writes a user's registered devices
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.device import Device


class DeviceRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # writes a new device to the database
    async def create(self, device: Device) -> Device:
        self._session.add(device)
        await self._session.flush()
        await self._session.refresh(device)
        return device

    # reads a device by its identifier
    async def get_by_id(self, device_id: uuid.UUID) -> Device | None:
        result = await self._session.execute(select(Device).where(Device.id == device_id).limit(1))
        return result.scalar_one_or_none()

    # lists every device a user has registered newest first
    async def get_all_by_user_id(self, user_id: uuid.UUID) -> list[Device]:
        result = await self._session.execute(
            select(Device).where(Device.user_id == user_id).order_by(Device.created_at.desc())
        )
        return list(result.scalars().all())

    # lists a user's devices that have not been revoked
    async def get_active_by_user_id(self, user_id: uuid.UUID) -> list[Device]:
        result = await self._session.execute(
            select(Device)
            .where(Device.user_id == user_id, Device.revoked_at.is_(None))
            .order_by(Device.created_at.desc())
        )
        return list(result.scalars().all())

    # revokes every active device of a user except one and returns their ids
    async def revoke_all_by_user_id(
        self, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> list[uuid.UUID]:
        stmt = select(Device).where(Device.user_id == user_id, Device.revoked_at.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(Device.id != exclude_id)
        result = await self._session.execute(stmt)
        devices = list(result.scalars().all())
        now = datetime.now(UTC)
        for device in devices:
            device.revoked_at = now
        await self._session.flush()
        return [device.id for device in devices]

    # reads a device by its public key
    async def get_by_public_key(self, public_key: bytes) -> Device | None:
        result = await self._session.execute(
            select(Device).where(Device.public_key == public_key).limit(1)
        )
        return result.scalar_one_or_none()

    # persists pending changes to a device
    async def save(self, device: Device) -> Device:
        await self._session.flush()
        await self._session.refresh(device)
        return device

    # deletes a device by its identifier
    async def delete_by_id(self, device_id: uuid.UUID) -> None:
        await self._session.execute(delete(Device).where(Device.id == device_id))
        await self._session.flush()
