# reads and writes a user's passkey credentials
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.passkey import PasskeyCredential


class PasskeyCredentialRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # writes a new passkey credential to the database
    async def create(self, credential: PasskeyCredential) -> PasskeyCredential:
        self._session.add(credential)
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    # reads a passkey credential by its webauthn credential id
    async def get_by_credential_id(self, credential_id: bytes) -> PasskeyCredential | None:
        result = await self._session.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.credential_id == credential_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    # persists pending changes to a passkey credential
    async def save(self, credential: PasskeyCredential) -> PasskeyCredential:
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    # lists every passkey a user has registered
    async def get_all_by_user_id(self, user_id: uuid.UUID) -> list[PasskeyCredential]:
        result = await self._session.execute(
            select(PasskeyCredential).where(PasskeyCredential.user_id == user_id)
        )
        return list(result.scalars().all())

    # reads a passkey credential by its identifier
    async def get_by_id(self, credential_id: uuid.UUID) -> PasskeyCredential | None:
        result = await self._session.execute(
            select(PasskeyCredential).where(PasskeyCredential.id == credential_id).limit(1)
        )
        return result.scalar_one_or_none()

    # counts how many passkeys a user has registered
    async def count_by_user_id(self, user_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(PasskeyCredential.user_id == user_id)
        )
        return result.scalar_one()

    # deletes a passkey credential by its identifier
    async def delete_by_id(self, credential_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(PasskeyCredential).where(PasskeyCredential.id == credential_id)
        )
        await self._session.flush()

    # checks whether a user has registered any passkey
    async def has_passkey(self, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(PasskeyCredential.id).where(PasskeyCredential.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    # deletes every passkey a user has registered
    async def delete_all_by_user_id(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(PasskeyCredential).where(PasskeyCredential.user_id == user_id)
        )
        await self._session.flush()
