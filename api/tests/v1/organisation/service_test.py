import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.organisation import (
    OrganisationMember,
    OrganisationRole,
)
from com.qode.qrew.v1.service.services.organisation import (
    OrganisationError,
    OrganisationService,
)


def _service_with(
    *,
    get_by_slug: object | None = None,
    get_member: object | None = None,
    get_user: object | None = None,
    owners_count: int = 1,
) -> tuple[OrganisationService, MagicMock, MagicMock, MagicMock, MagicMock]:
    org_repo = MagicMock()
    org_repo.get_by_slug = AsyncMock(return_value=get_by_slug)

    inserted_orgs: list[object] = []

    async def _insert_org(org: object) -> object:
        inserted_orgs.append(org)
        return org

    org_repo.insert = AsyncMock(side_effect=_insert_org)

    member_repo = MagicMock()
    member_repo.get = AsyncMock(return_value=get_member)

    async def _insert_member(**kwargs: Any) -> OrganisationMember:
        return OrganisationMember(**kwargs)

    member_repo.insert = AsyncMock(side_effect=_insert_member)
    member_repo.delete = AsyncMock(return_value=True)
    member_repo.count_owners = AsyncMock(return_value=owners_count)

    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=get_user)

    audit = MagicMock()
    audit.record = AsyncMock()

    return (
        OrganisationService(org_repo, member_repo, user_repo, audit),
        org_repo,
        member_repo,
        user_repo,
        audit,
    )


async def test_create_organisation_rejects_invalid_slug() -> None:
    service, *_ = _service_with()
    with pytest.raises(OrganisationError, match="Invalid slug"):
        await service.create_organisation(
            owner_id=uuid.uuid4(), slug="BadSlug!", name="x", description=None
        )


async def test_create_organisation_rejects_taken_slug() -> None:
    service, *_ = _service_with(get_by_slug=MagicMock())
    with pytest.raises(OrganisationError, match="Slug already taken"):
        await service.create_organisation(
            owner_id=uuid.uuid4(), slug="qrew", name="x", description=None
        )


async def test_create_organisation_inserts_owner_membership() -> None:
    owner_id = uuid.uuid4()
    service, _org_repo, member_repo, _, audit = _service_with()
    await service.create_organisation(
        owner_id=owner_id, slug="qrew", name="Qrew", description="hi"
    )
    member_repo.insert.assert_awaited_once()
    insert_kwargs = member_repo.insert.await_args.kwargs
    assert insert_kwargs["user_id"] == owner_id
    assert insert_kwargs["role"] == OrganisationRole.owner
    audit.record.assert_awaited_once()


async def test_invite_member_requires_existing_user() -> None:
    service, *_ = _service_with(get_user=None)
    with pytest.raises(OrganisationError, match="No user"):
        await service.invite_member(
            actor_id=uuid.uuid4(),
            organisation_id=uuid.uuid4(),
            invitee_email="ghost@example.com",
            role=OrganisationRole.member,
        )


async def test_invite_member_rejects_owner_role() -> None:
    service, *_ = _service_with(get_user=MagicMock(id=uuid.uuid4()))
    with pytest.raises(OrganisationError, match="Owners are promoted"):
        await service.invite_member(
            actor_id=uuid.uuid4(),
            organisation_id=uuid.uuid4(),
            invitee_email="x@example.com",
            role=OrganisationRole.owner,
        )


async def test_invite_member_rejects_duplicate() -> None:
    service, *_ = _service_with(
        get_user=MagicMock(id=uuid.uuid4()),
        get_member=OrganisationMember(
            organisation_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role=OrganisationRole.member,
        ),
    )
    with pytest.raises(OrganisationError, match="already a member"):
        await service.invite_member(
            actor_id=uuid.uuid4(),
            organisation_id=uuid.uuid4(),
            invitee_email="x@example.com",
            role=OrganisationRole.member,
        )


async def test_remove_member_refuses_to_drop_last_owner() -> None:
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    service, *_ = _service_with(
        get_member=OrganisationMember(
            organisation_id=org_id, user_id=user_id, role=OrganisationRole.owner
        ),
        owners_count=1,
    )
    with pytest.raises(OrganisationError, match="last owner"):
        await service.remove_member(
            actor_id=user_id,
            organisation_id=org_id,
            member_user_id=user_id,
        )


async def test_remove_member_allows_dropping_non_last_owner() -> None:
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    service, *_ = _service_with(
        get_member=OrganisationMember(
            organisation_id=org_id, user_id=user_id, role=OrganisationRole.owner
        ),
        owners_count=2,
    )
    await service.remove_member(
        actor_id=uuid.uuid4(),
        organisation_id=org_id,
        member_user_id=user_id,
    )
