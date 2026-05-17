import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.passkey import PasskeyCredential


class PasskeyCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, credential: PasskeyCredential) -> PasskeyCredential:
        """Persist a new PasskeyCredential."""
        self._session.add(credential)
        await self._session.flush()
        await self._session.refresh(credential)
        return credential

    async def get_by_credential_id(
        self, credential_id: bytes
    ) -> PasskeyCredential | None:
        """Return the credential matching the given credential ID bytes."""
        result = await self._session.execute(
            select(PasskeyCredential)
            .where(PasskeyCredential.credential_id == credential_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def has_passkey(self, user_id: uuid.UUID) -> bool:
        """Return True if the user has at least one registered passkey."""
        result = await self._session.execute(
            select(PasskeyCredential.id)
            .where(PasskeyCredential.user_id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
