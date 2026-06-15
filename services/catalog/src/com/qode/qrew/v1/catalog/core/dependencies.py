import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Path, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.catalog.core.database import get_db
from com.qode.qrew.v1.catalog.models.organisation import (
    OrganisationMember,
    OrganisationRole,
    role_rank,
)
from com.qode.qrew.v1.catalog.repositories.organisation import (
    OrganisationMemberRepository,
    OrganisationRepository,
)

limiter = Limiter(key_func=get_remote_address, enabled=True)

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"message": "Not a member of this organisation", "field": None},
)
_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"message": "Organisation not found", "field": "organisation_id"},
)


def get_org_member(
    minimum_role: OrganisationRole = OrganisationRole.member,
) -> Callable[..., Awaitable[OrganisationMember]]:
    async def _dependency(
        organisation_id: uuid.UUID = Path(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrganisationMember:
        org = await OrganisationRepository(db).get_by_id(organisation_id)
        if org is None:
            raise _NOT_FOUND
        member = await OrganisationMemberRepository(db).get(
            organisation_id, current_user.id
        )
        if member is None:
            raise _FORBIDDEN
        if role_rank(member.role) < role_rank(minimum_role):
            raise _FORBIDDEN
        return member

    return _dependency


from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from db import create_redis_dependency

get_redis = create_redis_dependency(settings.redis_url)
