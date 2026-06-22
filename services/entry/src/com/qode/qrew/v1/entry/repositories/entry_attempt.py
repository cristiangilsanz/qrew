from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.entry_attempt import EntryAttempt


class EntryAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, attempt: EntryAttempt) -> None:
        self._session.add(attempt)
        await self._session.flush()
