import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from com.qode.qrew.v1.service.core.auth import organisation_acl
from com.qode.qrew.v1.service.core.auth.organisation_acl import get_org_member
from com.qode.qrew.v1.service.models.organisation import (
    OrganisationMember,
    OrganisationRole,
)


def _user(user_id: uuid.UUID) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


def _org() -> MagicMock:
    org = MagicMock()
    org.deleted_at = None
    return org


def _member(role: OrganisationRole, user_id: uuid.UUID) -> OrganisationMember:
    return OrganisationMember(
        organisation_id=uuid.uuid4(),
        user_id=user_id,
        role=role,
    )


async def _invoke(
    dependency: Any,
    *,
    monkeypatch: pytest.MonkeyPatch,
    org_get_returns: Any,
    member_get_returns: Any,
    user_id: uuid.UUID,
) -> Any:
    org_repo = MagicMock()
    org_repo.get_by_id = AsyncMock(return_value=org_get_returns)
    member_repo = MagicMock()
    member_repo.get = AsyncMock(return_value=member_get_returns)

    def _org_repo_factory(_db: Any) -> MagicMock:
        return org_repo

    def _member_repo_factory(_db: Any) -> MagicMock:
        return member_repo

    monkeypatch.setattr(organisation_acl, "OrganisationRepository", _org_repo_factory)
    monkeypatch.setattr(
        organisation_acl, "OrganisationMemberRepository", _member_repo_factory
    )
    return await dependency(
        organisation_id=uuid.uuid4(),
        current_user=_user(user_id),
        db=MagicMock(),
    )


async def test_acl_allows_member_at_required_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    member = _member(OrganisationRole.manager, user_id)
    result = await _invoke(
        get_org_member(OrganisationRole.member),
        monkeypatch=monkeypatch,
        org_get_returns=_org(),
        member_get_returns=member,
        user_id=user_id,
    )
    assert result is member


async def test_acl_rejects_member_below_required_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    member = _member(OrganisationRole.member, user_id)
    with pytest.raises(HTTPException) as info:
        await _invoke(
            get_org_member(OrganisationRole.manager),
            monkeypatch=monkeypatch,
            org_get_returns=_org(),
            member_get_returns=member,
            user_id=user_id,
        )
    assert info.value.status_code == 403


async def test_acl_rejects_non_member(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(HTTPException) as info:
        await _invoke(
            get_org_member(OrganisationRole.member),
            monkeypatch=monkeypatch,
            org_get_returns=_org(),
            member_get_returns=None,
            user_id=uuid.uuid4(),
        )
    assert info.value.status_code == 403


async def test_acl_returns_404_when_org_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(HTTPException) as info:
        await _invoke(
            get_org_member(OrganisationRole.member),
            monkeypatch=monkeypatch,
            org_get_returns=None,
            member_get_returns=None,
            user_id=uuid.uuid4(),
        )
    assert info.value.status_code == 404
