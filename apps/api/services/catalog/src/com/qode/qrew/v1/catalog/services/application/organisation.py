# creates organisations and manages their membership
import re
import uuid
from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy import Select

from outbox import record as record_event

from com.qode.qrew.v1.catalog.models.outbox import EventOutbox
from com.qode.qrew.v1.catalog.services.application.audit import AuditService
from com.qode.qrew.v1.catalog.core.errors import DomainError
from observability import traced
from com.qode.qrew.v1.catalog.models.organisation import (
    Organisation,
    OrganisationMember,
    OrganisationRole,
)
from com.qode.qrew.v1.catalog.services.application.identity import (
    IdentityUnavailableError,
    resolve_user_id,
)
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
    # stores the repositories audit service and user resolver the service uses
    def __init__(
        self,
        org_repo: OrganisationRepository,
        member_repo: OrganisationMemberRepository,
        audit: AuditService,
        user_resolver: Callable[[str], Awaitable[uuid.UUID | None]] = resolve_user_id,
    ) -> None:
        self._orgs = org_repo
        self._members = member_repo
        self._audit = audit
        self._resolve_user = user_resolver

    # leaves in the outbox that an organisation's roster changed
    async def _publish_membership(
        self, *, organisation_id: uuid.UUID, user_id: uuid.UUID, role: str | None
    ) -> None:
        await record_event(
            self._members.session,
            EventOutbox,
            subject="catalog.membership.changed.v1",
            aggregate_type="organisation",
            aggregate_id=str(organisation_id),
            actor_id=str(user_id),
            data={
                "organisation_id": str(organisation_id),
                "user_id": str(user_id),
                "role": role,
            },
        )

    # builds the query that lists a user's organisations
    def list_for_user_query(self, user_id: uuid.UUID) -> Select[tuple[Organisation]]:
        return self._orgs.list_for_user_query(user_id)

    # builds the query that lists every organisation for a platform admin
    def list_all_query(self) -> Select[tuple[Organisation]]:
        return self._orgs.list_all_query()

    # reads an organisation by its identifier
    async def get_by_id(self, organisation_id: uuid.UUID) -> Organisation | None:
        return await self._orgs.get_by_id(organisation_id)

    # searches organisations by name or slug
    async def search(self, q: str, *, limit: int = 20) -> list[Organisation]:
        return await self._orgs.search(q, limit=limit)

    # lists an organisation's members
    async def list_members(self, organisation_id: uuid.UUID) -> list[MemberRow]:
        return await self._members.list_members(organisation_id)

    # creates an organisation with its owner as the first member
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
            raise OrganisationError("Slug rejected.", field="slug")
        existing = await self._orgs.get_by_slug(slug)
        if existing is not None:
            raise OrganisationError("Slug already taken.", field="slug")
        org = Organisation(slug=slug, name=name, description=description)
        org = await self._orgs.insert(org)
        await self._members.insert(
            organisation_id=org.id, user_id=owner_id, role=OrganisationRole.owner
        )
        await self._publish_membership(
            organisation_id=org.id, user_id=owner_id, role=str(OrganisationRole.owner)
        )
        await self._audit_safe(
            "organisation_created",
            actor_id=owner_id,
            organisation_id=org.id,
            payload={"slug": org.slug, "name": org.name},
        )
        return org

    # invites a user by email to join an organisation
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
            raise OrganisationError("Owner not invitable.", field="role")
        try:
            invitee_id = await self._resolve_user(invitee_email)
        except IdentityUnavailableError as exc:
            raise OrganisationError("Directory unavailable.", field=None) from exc
        if invitee_id is None:
            raise OrganisationError("User not found.", field="email")
        existing = await self._members.get(organisation_id, invitee_id)
        if existing is not None:
            raise OrganisationError("User already a member.", field="email")
        member = await self._members.insert(
            organisation_id=organisation_id, user_id=invitee_id, role=role
        )
        await self._audit_safe(
            "organisation_member_added",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(invitee_id), "role": str(role)},
        )
        await self._publish_membership(
            organisation_id=organisation_id, user_id=invitee_id, role=str(role)
        )
        return member

    # adds an already known user to an organisation
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
            raise OrganisationError("Owner not addable.", field="role")
        existing = await self._members.get(organisation_id, user_id)
        if existing is not None:
            raise OrganisationError("User already a member.", field="user_id")
        member = await self._members.insert(
            organisation_id=organisation_id, user_id=user_id, role=role
        )
        await self._audit_safe(
            "organisation_member_added",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(user_id), "role": str(role)},
        )
        await self._publish_membership(
            organisation_id=organisation_id, user_id=user_id, role=str(role)
        )
        return member

    # removes a member unless doing so would leave the organisation without an owner
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
            raise OrganisationError("User not a member.", field="user_id")
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
        await self._publish_membership(
            organisation_id=organisation_id, user_id=member_user_id, role=None
        )

    # soft deletes an organisation
    @traced("organisation.delete")
    async def delete_organisation(
        self,
        *,
        actor_id: uuid.UUID,
        organisation_id: uuid.UUID,
    ) -> None:
        deleted = await self._orgs.soft_delete(organisation_id)
        if not deleted:
            raise OrganisationError("Organisation not found.")
        await self._audit_safe(
            "organisation_deleted",
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={},
        )

    # records an audit event without letting a failure interrupt the caller
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
