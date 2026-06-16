import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.identity import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id).limit(1)
        )
        return result.scalar_one_or_none()
