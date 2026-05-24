import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.device import Device


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
