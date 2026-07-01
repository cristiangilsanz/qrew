import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.catalog.models.organisation import OrganisationRole
from com.qode.qrew.v1.catalog.services.application.organisation import (
    OrganisationError,
    OrganisationService,
)
from conftest import make_member, make_org


def _make_svc(
    *,
    org: object = None,
    org_by_slug: object = None,
    member: object = None,
    invitee: object = None,
    owner_count: int = 1,
) -> tuple[OrganisationService, MagicMock, MagicMock]:
    org_repo = MagicMock()
    org_repo.get_by_id = AsyncMock(return_value=org)
    org_repo.get_by_slug = AsyncMock(return_value=org_by_slug)
    org_repo.insert = AsyncMock(side_effect=lambda o: o)

    member_repo = MagicMock()
    member_repo.get = AsyncMock(return_value=member)
    member_repo.insert = AsyncMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    member_repo.delete = AsyncMock()
    member_repo.count_owners = AsyncMock(return_value=owner_count)

    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=invitee)

    audit = AsyncMock()
    audit.record = AsyncMock()

    svc = OrganisationService(
        org_repo=org_repo,
        member_repo=member_repo,
        user_repo=user_repo,
        audit=audit,
    )
    return svc, org_repo, member_repo


class TestOrganisationServiceCreate:
    async def test_raises_when_slug_invalid(self, actor_id: uuid.UUID) -> None:
        svc, _, _ = _make_svc()
        with pytest.raises(OrganisationError, match="slug"):
            await svc.create_organisation(
                owner_id=actor_id, slug="A", name="Acme", description=None
            )

    async def test_raises_when_slug_starts_with_digit(self, actor_id: uuid.UUID) -> None:
        svc, _, _ = _make_svc()
        with pytest.raises(OrganisationError, match="slug"):
            await svc.create_organisation(
                owner_id=actor_id, slug="1acme", name="Acme", description=None
            )

    async def test_raises_when_slug_taken(self, actor_id: uuid.UUID) -> None:
        existing = make_org(slug="acme")
        svc, _, _ = _make_svc(org_by_slug=existing)
        with pytest.raises(OrganisationError, match="taken"):
            await svc.create_organisation(
                owner_id=actor_id, slug="acme", name="Acme", description=None
            )

    async def test_creates_org_and_adds_owner_member(self, actor_id: uuid.UUID) -> None:
        svc, org_repo, member_repo = _make_svc(org_by_slug=None)
        result = await svc.create_organisation(
            owner_id=actor_id, slug="acme-org", name="Acme", description=None
        )
        assert result.slug == "acme-org"
        org_repo.insert.assert_awaited_once()
        member_repo.insert.assert_awaited_once()
        _, kwargs = member_repo.insert.call_args
        assert kwargs["user_id"] == actor_id
        assert kwargs["role"] == OrganisationRole.owner


class TestOrganisationServiceInviteMember:
    async def test_raises_when_inviting_as_owner(
        self, actor_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc()
        with pytest.raises(OrganisationError, match="promoted"):
            await svc.invite_member(
                actor_id=actor_id,
                organisation_id=org_id,
                invitee_email="x@example.com",
                role=OrganisationRole.owner,
            )

    async def test_raises_when_user_not_found(self, actor_id: uuid.UUID, org_id: uuid.UUID) -> None:
        svc, _, _ = _make_svc(invitee=None)
        with pytest.raises(OrganisationError, match="email"):
            await svc.invite_member(
                actor_id=actor_id,
                organisation_id=org_id,
                invitee_email="nobody@example.com",
                role=OrganisationRole.member,
            )

    async def test_raises_when_already_member(self, actor_id: uuid.UUID, org_id: uuid.UUID) -> None:
        invitee = SimpleNamespace(id=uuid.uuid4(), email="user@example.com")
        existing_member = make_member(org_id=org_id, user_id=invitee.id)
        svc, _, _ = _make_svc(invitee=invitee, member=existing_member)
        with pytest.raises(OrganisationError, match="already a member"):
            await svc.invite_member(
                actor_id=actor_id,
                organisation_id=org_id,
                invitee_email="user@example.com",
                role=OrganisationRole.member,
            )

    async def test_adds_member(self, actor_id: uuid.UUID, org_id: uuid.UUID) -> None:
        invitee = SimpleNamespace(id=uuid.uuid4(), email="new@example.com")
        svc, _, member_repo = _make_svc(invitee=invitee, member=None)
        await svc.invite_member(
            actor_id=actor_id,
            organisation_id=org_id,
            invitee_email="new@example.com",
            role=OrganisationRole.member,
        )
        member_repo.insert.assert_awaited_once()
        _, kwargs = member_repo.insert.call_args
        assert kwargs["user_id"] == invitee.id
        assert kwargs["role"] == OrganisationRole.member


class TestOrganisationServiceRemoveMember:
    async def test_raises_when_not_a_member(self, actor_id: uuid.UUID, org_id: uuid.UUID) -> None:
        svc, _, _ = _make_svc(member=None)
        with pytest.raises(OrganisationError, match="not a member"):
            await svc.remove_member(
                actor_id=actor_id,
                organisation_id=org_id,
                member_user_id=uuid.uuid4(),
            )

    async def test_raises_when_removing_last_owner(
        self, actor_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        target_id = uuid.uuid4()
        member = make_member(org_id=org_id, user_id=target_id, role=OrganisationRole.owner)
        svc, _, _ = _make_svc(member=member, owner_count=1)
        with pytest.raises(OrganisationError, match="last owner"):
            await svc.remove_member(
                actor_id=actor_id,
                organisation_id=org_id,
                member_user_id=target_id,
            )

    async def test_allows_removing_owner_when_others_exist(
        self, actor_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        target_id = uuid.uuid4()
        member = make_member(org_id=org_id, user_id=target_id, role=OrganisationRole.owner)
        svc, _, member_repo = _make_svc(member=member, owner_count=2)
        await svc.remove_member(actor_id=actor_id, organisation_id=org_id, member_user_id=target_id)
        member_repo.delete.assert_awaited_once_with(org_id, target_id)

    async def test_removes_regular_member(self, actor_id: uuid.UUID, org_id: uuid.UUID) -> None:
        target_id = uuid.uuid4()
        member = make_member(org_id=org_id, user_id=target_id, role=OrganisationRole.member)
        svc, _, member_repo = _make_svc(member=member)
        await svc.remove_member(actor_id=actor_id, organisation_id=org_id, member_user_id=target_id)
        member_repo.delete.assert_awaited_once_with(org_id, target_id)
