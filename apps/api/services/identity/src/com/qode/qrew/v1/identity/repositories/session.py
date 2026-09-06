# reads and writes a user's login sessions
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.session import Session


class SessionRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # writes a new session to the database
    async def create(self, session: Session) -> Session:
        self._session.add(session)
        await self._session.flush()
        await self._session.refresh(session)
        return session

    # reads a session by its refresh token identifier
    async def get_by_jti(self, jti: str) -> Session | None:
        result = await self._session.execute(select(Session).where(Session.jti == jti).limit(1))
        return result.scalar_one_or_none()

    # lists a user's sessions most recently used first
    async def get_all_by_user_id(self, user_id: uuid.UUID) -> list[Session]:
        result = await self._session.execute(
            select(Session).where(Session.user_id == user_id).order_by(Session.last_used_at.desc())
        )
        return list(result.scalars().all())

    # counts how many sessions a user has open
    async def count_by_user_id(self, user_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Session).where(Session.user_id == user_id)
        )
        return int(result.scalar_one())

    # lists a user's oldest sessions up to a limit
    async def get_oldest_by_user_id(self, user_id: uuid.UUID, limit: int) -> list[Session]:
        result = await self._session.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # rotates a session's refresh token identifier
    async def update_jti(self, old_jti: str, new_jti: str) -> None:
        result = await self._session.execute(select(Session).where(Session.jti == old_jti).limit(1))
        session = result.scalar_one_or_none()
        if session is not None:
            session.jti = new_jti
            session.last_used_at = datetime.now(UTC)
            await self._session.flush()

    # records when a session last reasserted its passkey
    async def update_last_asserted_at(self, jti: str, asserted_at: datetime) -> None:
        result = await self._session.execute(select(Session).where(Session.jti == jti).limit(1))
        session = result.scalar_one_or_none()
        if session is not None:
            session.last_asserted_at = asserted_at
            await self._session.flush()

    # deletes a session by its refresh token identifier
    async def delete_by_jti(self, jti: str) -> None:
        await self._session.execute(delete(Session).where(Session.jti == jti))
        await self._session.flush()

    # deletes every session bound to a device and returns their identifiers
    async def delete_by_device_id(self, device_id: uuid.UUID) -> list[str]:
        result = await self._session.execute(
            select(Session.jti).where(Session.device_id == device_id)
        )
        jtis = list(result.scalars().all())
        await self._session.execute(delete(Session).where(Session.device_id == device_id))
        await self._session.flush()
        return jtis

    # deletes every session of a user and returns their identifiers
    async def delete_all_by_user_id(self, user_id: uuid.UUID) -> list[str]:
        result = await self._session.execute(select(Session.jti).where(Session.user_id == user_id))
        jtis = list(result.scalars().all())
        await self._session.execute(delete(Session).where(Session.user_id == user_id))
        await self._session.flush()
        return jtis
