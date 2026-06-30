import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.models.organisation import (
    Organisation,
    OrganisationMember,
    OrganisationRole,
)


class OrganisationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organisation_id: uuid.UUID) -> Organisation | None:
        result = await self._session.execute(
            select(Organisation).where(
                Organisation.id == organisation_id,
                Organisation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organisation | None:
        result = await self._session.execute(
            select(Organisation).where(
                Organisation.slug == slug,
                Organisation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def insert(self, organisation: Organisation) -> Organisation:
        self._session.add(organisation)
        await self._session.flush()
        await self._session.refresh(organisation)
        return organisation

    def list_for_user_query(self, user_id: uuid.UUID):  # type: ignore[no-untyped-def]
        return (
            select(Organisation)
            .join(
                OrganisationMember,
                OrganisationMember.organisation_id == Organisation.id,
            )
            .where(
                OrganisationMember.user_id == user_id,
                Organisation.deleted_at.is_(None),
            )
        )


class OrganisationMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, organisation_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganisationMember | None:
        result = await self._session.execute(
            select(OrganisationMember).where(
                OrganisationMember.organisation_id == organisation_id,
                OrganisationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def insert(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: OrganisationRole,
    ) -> OrganisationMember:
        member = OrganisationMember(organisation_id=organisation_id, user_id=user_id, role=role)
        self._session.add(member)
        await self._session.flush()
        await self._session.refresh(member)
        return member

    async def delete(self, organisation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = await self.get(organisation_id, user_id)
        if member is None:
            return False
        await self._session.delete(member)
        await self._session.flush()
        return True

    async def count_owners(self, organisation_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(OrganisationMember).where(
                OrganisationMember.organisation_id == organisation_id,
                OrganisationMember.role == OrganisationRole.owner,
            )
        )
        return len(list(result.scalars().all()))
