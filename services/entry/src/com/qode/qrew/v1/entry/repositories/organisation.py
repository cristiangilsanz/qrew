import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.models.catalog import OrganisationMember


class OrganisationMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, organisation_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganisationMember | None:
        result = await self._session.execute(
            select(OrganisationMember)
            .where(
                OrganisationMember.organisation_id == organisation_id,
                OrganisationMember.user_id == user_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
