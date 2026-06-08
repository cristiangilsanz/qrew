import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.models.organisation import (
    OrganisationMember,
    OrganisationRole,
    role_rank,
)
from com.qode.qrew.v1.service.repositories.organisation import (
    OrganisationMemberRepository,
    OrganisationRepository,
)

_FORBIDDEN_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"message": "Not a member of this organisation", "field": None},
)
_NOT_FOUND_EXCEPTION = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"message": "Organisation not found", "field": "organisation_id"},
)


def get_org_member(
    minimum_role: OrganisationRole = OrganisationRole.member,
) -> Callable[..., Awaitable[OrganisationMember]]:
    """Build a FastAPI dependency that gates a route on org membership and role."""

    async def _dependency(
        organisation_id: uuid.UUID = Path(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrganisationMember:
        org = await OrganisationRepository(db).get_by_id(organisation_id)
        if org is None:
            raise _NOT_FOUND_EXCEPTION
        member = await OrganisationMemberRepository(db).get(
            organisation_id, current_user.id
        )
        if member is None:
            raise _FORBIDDEN_EXCEPTION
        if role_rank(member.role) < role_rank(minimum_role):
            raise _FORBIDDEN_EXCEPTION
        return member

    return _dependency
