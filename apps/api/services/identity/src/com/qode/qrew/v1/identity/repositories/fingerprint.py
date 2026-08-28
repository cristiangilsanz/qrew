# reads and writes the device fingerprints used to detect multi account abuse
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.fingerprint import DeviceFingerprint


class DeviceFingerprintRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # records a fingerprint sighting and returns how many accounts share it
    async def upsert(self, record: DeviceFingerprint) -> int:
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

    # lists the distinct users who share a fingerprint
    async def get_user_ids_by_hash(self, fingerprint_hash: str) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(DeviceFingerprint.user_id.distinct()).where(
                DeviceFingerprint.fingerprint_hash == fingerprint_hash
            )
        )
        return list(result.scalars().all())
