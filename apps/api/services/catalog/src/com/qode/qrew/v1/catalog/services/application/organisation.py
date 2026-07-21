import re
import uuid

import structlog
from sqlalchemy import Select

from com.qode.qrew.v1.catalog.services.application.audit import AuditService
from com.qode.qrew.v1.catalog.core.errors import DomainError
from observability import traced
from com.qode.qrew.v1.catalog.models.organisation import (
    Organisation,
    OrganisationMember,
    OrganisationRole,
)
from com.qode.qrew.v1.catalog.repositories.identity import UserRepository
from com.qode.qrew.v1.catalog.repositories.organisation import (
    MemberRow,
    OrganisationMemberRepository,
    OrganisationRepository,
)

logger = structlog.get_logger(__name__)

_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")


class OrganisationError(DomainError):
    pass


class OrganisationService:
    def __init__(
        self,
        org_repo: OrganisationRepository,
        member_repo: OrganisationMemberRepository,
        user_repo: UserRepository,
        audit: AuditService,
    ) -> None:
        self._orgs = org_repo
        self._members = member_repo
        self._users = user_repo
        self._audit = audit

    def list_for_user_query(self, user_id: uuid.UUID) -> Select[tuple[Organisation]]:
        return self._orgs.list_for_user_query(user_id)

    async def get_by_id(self, organisation_id: uuid.UUID) -> Organisation | None:
        return await self._orgs.get_by_id(organisation_id)

    async def search(self, q: str, *, limit: int = 20) -> list[Organisation]:
        return await self._orgs.search(q, limit=limit)

    async def list_members(self, organisation_id: uuid.UUID) -> list[MemberRow]:
        return await self._members.list_members(organisation_id)

    @traced("organisation.create")
    async def create_organisation(
        self,
        *,
        owner_id: uuid.UUID,
        slug: str,
        name: str,
        description: str | None,
    ) -> Organisation:
        if not _SLUG_PATTERN.fullmatch(slug):
            raise OrganisationError("Invalid slug", field="slug")
        existing = await self._orgs.get_by_slug(slug)
        if existing is not None:
            raise OrganisationError("Slug already taken", field="slug")
        org = Organisation(slug=slug, name=name, description=description)
        org = await self._orgs.insert(org)
        await self._members.insert(
            organisation_id=org.id, user_id=owner_id, role=OrganisationRole.owner
        )
        await self._audit_safe(
            "organisation_created",
            actor_id=owner_id,
            organisation_id=org.id,
            payload={"slug": org.slug, "name": org.name},
        )
        return org

    @traced("organisation.invite_member")
    async def invite_member(
        self,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
        invitee_email: str,
        role: OrganisationRole,
    ) -> OrganisationMember:
        if role == OrganisationRole.owner:
            raise OrganisationError("Owners are promoted, not invited", field="role")
        invitee = await self._users.get_by_email(invitee_email)
        if invitee is None:
            raise OrganisationError("No user with this email", field="email")
        existing = await self._members.get(organisation_id, invitee.id)
        if existing is not None:
            raise OrganisationError("User is already a member of this organisation", field="email")
        member = await self._members.insert(
            organisation_id=organisation_id, user_id=invitee.id, role=role
        )
        await self._audit_safe(
            "organisation_member_added",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(invitee.id), "role": str(role)},
        )
        return member

    @traced("organisation.add_member")
    async def add_member(
        self,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: OrganisationRole,
    ) -> OrganisationMember:
        if role == OrganisationRole.owner:
            raise OrganisationError("Owners are promoted, not added", field="role")
        existing = await self._members.get(organisation_id, user_id)
        if existing is not None:
            raise OrganisationError("User is already a member of this organisation", field="user_id")
        member = await self._members.insert(
            organisation_id=organisation_id, user_id=user_id, role=role
        )
        await self._audit_safe(
            "organisation_member_added",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(user_id), "role": str(role)},
        )
        return member

    @traced("organisation.remove_member")
    async def remove_member(
        self,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
        member_user_id: uuid.UUID,
    ) -> None:
        member = await self._members.get(organisation_id, member_user_id)
        if member is None:
            raise OrganisationError("User is not a member of this organisation", field="user_id")
        if member.role == OrganisationRole.owner:
            owners = await self._members.count_owners(organisation_id)
            if owners <= 1:
                raise OrganisationError(
                    "Cannot remove the last owner of an organisation", field="user_id"
                )
        await self._members.delete(organisation_id, member_user_id)
        await self._audit_safe(
            "organisation_member_removed",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(member_user_id)},
        )

    @traced("organisation.delete")
    async def delete_organisation(
        self,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
    ) -> None:
        deleted = await self._orgs.soft_delete(organisation_id)
        if not deleted:
            raise OrganisationError("Organisation not found")
        await self._audit_safe(
            "organisation_deleted",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={},
        )

    async def _audit_safe(
        self,
        action: str,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
        payload: dict[str, object],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="organisation",
                entity_id=str(organisation_id),
                payload=payload,
            )
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))
