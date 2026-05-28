import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.auth.session import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: Session) -> Session:
        """Persist a new Session."""
        self._session.add(session)
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def get_by_jti(self, jti: str) -> Session | None:
        """Return the session matching the given JTI."""
        result = await self._session.execute(
            select(Session).where(Session.jti == jti).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_by_user_id(self, user_id: uuid.UUID) -> list[Session]:
        """Return all sessions for the given user ordered."""
        result = await self._session.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.last_used_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_user_id(self, user_id: uuid.UUID) -> int:
        """Return the number of sessions persisted for the given user."""
        result = await self._session.execute(
            select(func.count()).select_from(Session).where(Session.user_id == user_id)
        )
        return int(result.scalar_one())

    async def get_oldest_by_user_id(
        self, user_id: uuid.UUID, limit: int
    ) -> list[Session]:
        """Return the user's oldest sessions, ordered by created_at ASC."""
        result = await self._session.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_jti(self, old_jti: str, new_jti: str) -> None:
        """Rotate the token identifier of a session and stamp last used."""
        result = await self._session.execute(
            select(Session).where(Session.jti == old_jti).limit(1)
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.jti = new_jti
            session.last_used_at = datetime.now(UTC)
            await self._session.flush()

    async def update_last_asserted_at(self, jti: str, asserted_at: datetime) -> None:
        """Stamp the last passkey re-assertion timestamp on the given session."""
        result = await self._session.execute(
            select(Session).where(Session.jti == jti).limit(1)
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.last_asserted_at = asserted_at
            await self._session.flush()

    async def delete_by_jti(self, jti: str) -> None:
        """Delete the session with the given JTI."""
        await self._session.execute(delete(Session).where(Session.jti == jti))
        await self._session.flush()

    async def delete_all_by_user_id(self, user_id: uuid.UUID) -> list[str]:
        """Delete all sessions for the user and return their JTIs."""
        result = await self._session.execute(
            select(Session.jti).where(Session.user_id == user_id)
        )
        jtis = list(result.scalars().all())
        await self._session.execute(delete(Session).where(Session.user_id == user_id))
        await self._session.flush()
        return jtis
