from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists_by_email(self, email: str) -> bool:
        """Return True if a user with the given email exists."""
        result = await self._session.execute(
            select(User.id).where(User.email == email).limit(1)
        )
        return result.scalar() is not None

    async def exists_by_phone(self, phone_number: str) -> bool:
        """Return True if a user with the given phone number exists."""
        result = await self._session.execute(
            select(User.id).where(User.phone_number == phone_number).limit(1)
        )
        return result.scalar() is not None

    async def get_by_email(self, email: str) -> User | None:
        """Return the user matching the given email address."""
        result = await self._session.execute(
            select(User).where(User.email == email).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_email_verification_token(self, token: str) -> User | None:
        """Return the user matching the given email verification token."""
        result = await self._session.execute(
            select(User).where(User.email_verification_token == token).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Return the user matching the given phone number."""
        result = await self._session.execute(
            select(User).where(User.phone_number == phone_number).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new User."""
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        """Flush pending changes for an already-tracked User."""
        await self._session.flush()
        await self._session.refresh(user)
        return user
