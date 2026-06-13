import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.gate.models.scanner import Scanner


class ScannerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, scanner: Scanner) -> Scanner:
        self._session.add(scanner)
        await self._session.flush()
        await self._session.refresh(scanner)
        return scanner

    async def get_by_id(self, scanner_id: uuid.UUID) -> Scanner | None:
        result = await self._session.execute(
            select(Scanner).where(Scanner.id == scanner_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Scanner]:
        result = await self._session.execute(
            select(Scanner).order_by(Scanner.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate(self, scanner: Scanner) -> Scanner:
        scanner.is_active = False
        await self._session.flush()
        await self._session.refresh(scanner)
        return scanner

    async def touch_last_used(self, scanner: Scanner) -> None:
        scanner.last_used_at = datetime.now(UTC)
        await self._session.flush()

    async def save(self, scanner: Scanner) -> Scanner:
        await self._session.flush()
        await self._session.refresh(scanner)
        return scanner
