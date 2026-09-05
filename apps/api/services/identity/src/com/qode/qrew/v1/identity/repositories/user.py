# reads and writes users
import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.models.user import KycStatus, User


class UserRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # hands the session out, so a caller can leave an event in the same transaction
    @property
    def session(self) -> AsyncSession:
        return self._session

    # reads a user by their identifier
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id).limit(1))
        return result.scalar_one_or_none()

    # checks whether a user already exists with this email
    async def exists_by_email(self, email: str) -> bool:
        result = await self._session.execute(
            select(User.id).where(User.email_hash == pii_crypto.hash_lookup(email)).limit(1)
        )
        return result.scalar() is not None

    # checks whether a user already exists with this phone number
    async def exists_by_phone(self, phone_number: str) -> bool:
        result = await self._session.execute(
            select(User.id)
            .where(User.phone_number_hash == pii_crypto.hash_lookup(phone_number))
            .limit(1)
        )
        return result.scalar() is not None

    # reads a user by their email
    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email_hash == pii_crypto.hash_lookup(email)).limit(1)
        )
        return result.scalar_one_or_none()

    # reads a user by their pending email verification token
    async def get_by_email_verification_token(self, token: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(User.email_verification_token == pii_crypto.hash_lookup(token))
            .limit(1)
        )
        return result.scalar_one_or_none()

    # reads a user by their phone number
    async def get_by_phone_number(self, phone_number: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(User.phone_number_hash == pii_crypto.hash_lookup(phone_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    # writes a new user to the database
    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    # reads a user by their pending email change token
    async def get_by_pending_email_token(self, token: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(User.pending_email_verification_token == pii_crypto.hash_lookup(token))
            .limit(1)
        )
        return result.scalar_one_or_none()

    # reads a user by their password reset token
    async def get_by_password_reset_token(self, token: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.password_reset_token == pii_crypto.hash_lookup(token)).limit(1)
        )
        return result.scalar_one_or_none()

    # reads a user by the hash of their national identity number
    async def get_by_national_id_hash(self, national_id_hash: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.national_id_hash == national_id_hash).limit(1)
        )
        return result.scalar_one_or_none()

    # reads every user among a list of identifiers
    async def get_by_ids(self, user_ids: list[uuid.UUID]) -> list[User]:
        if not user_ids:
            return []
        result = await self._session.execute(select(User).where(User.id.in_(user_ids)))
        return list(result.scalars().all())

    # searches users whose email or name partially matches the query
    async def search_by_email_partial(self, q: str, *, limit: int = 50) -> list[User]:
        pattern = q.strip().lower()
        matches: list[User] = []
        batch_size = 500
        offset = 0
        while len(matches) < limit:
            result = await self._session.execute(
                select(User).order_by(User.created_at.desc()).limit(batch_size).offset(offset)
            )
            batch = list(result.scalars())
            if not batch:
                break
            for u in batch:
                if pattern in u.email.lower() or pattern in u.full_name.lower():
                    matches.append(u)
                    if len(matches) >= limit:
                        break
            offset += batch_size
        return matches

    # persists pending changes to a user
    async def save(self, user: User) -> User:
        await self._session.flush()
        await self._session.refresh(user)
        return user

    # builds the query that searches users by email and kyc status
    def search_query(
        self,
        search: str | None = None,
        kyc_status: KycStatus | None = None,
    ) -> Select[tuple[User]]:
        stmt = select(User)
        if search:
            stmt = stmt.where(User.email_hash == pii_crypto.hash_lookup(search))
        if kyc_status is not None:
            stmt = stmt.where(User.kyc_status == kyc_status)
        return stmt
