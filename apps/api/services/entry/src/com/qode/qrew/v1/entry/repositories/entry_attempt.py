# records every entry attempt made at a control device
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.entry_attempt import EntryAttempt


class EntryAttemptRepository:
    # stores the session the repository queries through
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # writes an entry attempt to the database
    async def record(self, attempt: EntryAttempt) -> None:
        self._session.add(attempt)
        await self._session.flush()
