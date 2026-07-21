import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.models.user import KycStatus, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return the user matching the given identifier."""
        result = await self._session.execute(select(User).where(User.id == user_id).limit(1))
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Check whether a user with the given email already exists."""
        result = await self._session.execute(
            select(User.id).where(User.email_hash == pii_crypto.hash_lookup(email)).limit(1)
        )
        return result.scalar() is not None

    async def exists_by_phone(self, phone_number: str) -> bool:
        """Check whether a user with the given phone number already exists."""
        result = await self._session.execute(
            select(User.id)
            .where(User.phone_number_hash == pii_crypto.hash_lookup(phone_number))
            .limit(1)
        )
        return result.scalar() is not None

    async def get_by_email(self, email: str) -> User | None:
        """Return the user matching the given email address."""
        result = await self._session.execute(
            select(User).where(User.email_hash == pii_crypto.hash_lookup(email)).limit(1)
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
            select(User)
            .where(User.phone_number_hash == pii_crypto.hash_lookup(phone_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new user record to the database."""
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
        """Return the user matching the given national ID hash."""
        result = await self._session.execute(
            select(User).where(User.national_id_hash == national_id_hash).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, user_ids: list[uuid.UUID]) -> list[User]:
        """Return all users matching the given ids (order not guaranteed)."""
        if not user_ids:
            return []
        result = await self._session.execute(select(User).where(User.id.in_(user_ids)))
        return list(result.scalars().all())

    async def search_by_email_partial(self, q: str, *, limit: int = 50) -> list[User]:
        """Return users whose decrypted email/name contains q; all users when q is empty."""
        result = await self._session.execute(select(User))
        pattern = q.strip().lower()
        if not pattern:
            return list(result.scalars())[:limit]
        return [
            u for u in result.scalars()
            if pattern in u.email.lower() or pattern in u.full_name.lower()
        ][:limit]

    async def save(self, user: User) -> User:
        """Persist pending changes for an already-tracked user."""
        await self._session.flush()
        await self._session.refresh(user)
        return user

    def search_query(
        self,
        search: str | None = None,
        kyc_status: KycStatus | None = None,
    ) -> Select[tuple[User]]:
        """Build a filtered users query for use by the pagination helper."""
        stmt = select(User)
        if search:
            stmt = stmt.where(User.email_hash == pii_crypto.hash_lookup(search))
        if kyc_status is not None:
            stmt = stmt.where(User.kyc_status == kyc_status)
        return stmt
