import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.device.fingerprint import DeviceFingerprint


class DeviceFingerprintRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, record: DeviceFingerprint) -> int:
        """Saves or updates a device fingerprint entry and returns how many distinct users share that fingerprint."""
        stmt = (
            insert(DeviceFingerprint)
            .values(
                id=record.id,
                user_id=record.user_id,
                fingerprint_hash=record.fingerprint_hash,
                user_agent=record.user_agent,
                ip_address=record.ip_address,
                seen_at=datetime.now(UTC),
                account_count_at_seen=record.account_count_at_seen,
            )
            .on_conflict_do_update(
                constraint="uq_device_fingerprints_user_hash",
                set_={
                    "user_agent": record.user_agent,
                    "ip_address": record.ip_address,
                    "seen_at": datetime.now(UTC),
                    "account_count_at_seen": record.account_count_at_seen,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

        count_result = await self._session.execute(
            select(func.count(DeviceFingerprint.user_id.distinct())).where(
                DeviceFingerprint.fingerprint_hash == record.fingerprint_hash
            )
        )
        return count_result.scalar_one()

    async def get_user_ids_by_hash(self, fingerprint_hash: str) -> list[uuid.UUID]:
        """Returns all distinct user identifiers associated with a given device fingerprint."""
        result = await self._session.execute(
            select(DeviceFingerprint.user_id.distinct()).where(
                DeviceFingerprint.fingerprint_hash == fingerprint_hash
            )
        )
        return list(result.scalars().all())
