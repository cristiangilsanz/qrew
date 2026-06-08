import re
import uuid

import structlog

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.organisation import (
    Organisation,
    OrganisationMember,
    OrganisationRole,
)
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.repositories.organisation import (
    OrganisationMemberRepository,
    OrganisationRepository,
)
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)

_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")


class OrganisationError(DomainError):
    """Raised when an organisation operation fails a domain rule."""


class OrganisationService:
    """Business logic for organisations and their membership."""

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

    @traced("organisation.create")
    async def create_organisation(
        self,
        *,
        owner_id: uuid.UUID,
        slug: str,
        name: str,
        description: str | None,
    ) -> Organisation:
        """Create a new organisation with the caller as its sole owner."""
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
            AuditAction.ORGANISATION_CREATED,
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
        """Add an existing user to an organisation with the requested role."""
        if role == OrganisationRole.owner:
            raise OrganisationError("Owners are promoted, not invited", field="role")
        invitee = await self._users.get_by_email(invitee_email)
        if invitee is None:
            raise OrganisationError("No user with this email", field="email")
        existing = await self._members.get(organisation_id, invitee.id)
        if existing is not None:
            raise OrganisationError(
                "User is already a member of this organisation",
                field="email",
            )
        member = await self._members.insert(
            organisation_id=organisation_id, user_id=invitee.id, role=role
        )
        await self._audit_safe(
            AuditAction.ORGANISATION_MEMBER_ADDED,
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(invitee.id), "role": str(role)},
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
        """Remove a member; refuse to drop the last owner of an organisation."""
        member = await self._members.get(organisation_id, member_user_id)
        if member is None:
            raise OrganisationError(
                "User is not a member of this organisation",
                field="user_id",
            )
        if member.role == OrganisationRole.owner:
            owners = await self._members.count_owners(organisation_id)
            if owners <= 1:
                raise OrganisationError(
                    "Cannot remove the last owner of an organisation",
                    field="user_id",
                )
        await self._members.delete(organisation_id, member_user_id)
        await self._audit_safe(
            AuditAction.ORGANISATION_MEMBER_REMOVED,
            actor_id=actor_id,
            organisation_id=organisation_id,
            payload={"member_user_id": str(member_user_id)},
        )

    async def _audit_safe(
        self,
        action: AuditAction,
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
        except Exception:
            await logger.awarning("audit_write_failed", action=action)
