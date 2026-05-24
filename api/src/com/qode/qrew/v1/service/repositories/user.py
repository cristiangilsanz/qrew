import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.user import KycStatus, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return the user matching the given UUID."""
        result = await self._session.execute(
            select(User).where(User.id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

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

    async def get_by_pending_email_token(self, token: str) -> User | None:
        """Return the user matching the given pending email verification token."""
        result = await self._session.execute(
            select(User).where(User.pending_email_verification_token == token).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_national_id_hash(self, national_id_hash: str) -> User | None:
        """Return the user matching the given national ID hash, or None."""
        result = await self._session.execute(
            select(User).where(User.national_id_hash == national_id_hash).limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, user: User) -> User:
        """Flush pending changes for an already-tracked User."""
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def search_paginated(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        kyc_status: KycStatus | None = None,
    ) -> tuple[list[User], int]:
        """Return a page of users matching optional filters, plus the total count."""
        base = select(User)
        if search:
            pattern = f"%{search}%"
            base = base.where(
                or_(User.email.ilike(pattern), User.full_name.ilike(pattern))
            )
        if kyc_status is not None:
            base = base.where(User.kyc_status == kyc_status)

        count_result = await self._session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        rows = await self._session.execute(
            base.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.scalars().all()), total
