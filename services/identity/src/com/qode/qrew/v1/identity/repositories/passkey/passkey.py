import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.models.passkey.passkey import PasskeyCredential


class PasskeyCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, credential: PasskeyCredential) -> PasskeyCredential:
        """Persists a new passkey credential to the database."""
        self._session.add(credential)
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    async def get_by_credential_id(self, credential_id: bytes) -> PasskeyCredential | None:
        """Return the credential matching the given credential ID bytes."""
        result = await self._session.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.credential_id == credential_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, credential: PasskeyCredential) -> PasskeyCredential:
        """Persists pending changes for an already-tracked passkey credential."""
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    async def get_all_by_user_id(self, user_id: uuid.UUID) -> list[PasskeyCredential]:
        """Return all credentials belonging to the given user."""
        result = await self._session.execute(
            select(PasskeyCredential).where(PasskeyCredential.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, credential_id: uuid.UUID) -> PasskeyCredential | None:
        """Return the credential matching the given UUID primary key."""
        result = await self._session.execute(
            select(PasskeyCredential).where(PasskeyCredential.id == credential_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def count_by_user_id(self, user_id: uuid.UUID) -> int:
        """Return the number of credentials belonging to the given user."""
        result = await self._session.execute(
            select(func.count()).where(PasskeyCredential.user_id == user_id)
        )
        return result.scalar_one()

    async def delete_by_id(self, credential_id: uuid.UUID) -> None:
        """Delete the credential with the given UUID primary key."""
        await self._session.execute(
            delete(PasskeyCredential).where(PasskeyCredential.id == credential_id)
        )
        await self._session.flush()

    async def has_passkey(self, user_id: uuid.UUID) -> bool:
        """Checks whether the user has at least one registered passkey."""
        result = await self._session.execute(
            select(PasskeyCredential.id).where(PasskeyCredential.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def delete_all_by_user_id(self, user_id: uuid.UUID) -> None:
        """Delete all passkey credentials belonging to the given user."""
        await self._session.execute(
            delete(PasskeyCredential).where(PasskeyCredential.user_id == user_id)
        )
        await self._session.flush()
