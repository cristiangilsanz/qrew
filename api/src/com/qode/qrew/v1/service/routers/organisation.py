import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.api import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.auth.organisation_acl import get_org_member
from com.qode.qrew.v1.service.core.idempotency import idempotent
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.ratelimit import rate_limit
from com.qode.qrew.v1.service.core.ratelimit.dependencies import (
    audit_on_rejection,
    limiter_for,
)
from com.qode.qrew.v1.service.models.auth.user import User
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
from com.qode.qrew.v1.service.schemas.organisation import (
    OrganisationCreateRequest,
    OrganisationMemberInviteRequest,
    OrganisationMemberResponse,
    OrganisationPublicResponse,
    OrganisationResponse,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.organisation import (
    OrganisationError,
    OrganisationService,
)

router = APIRouter(prefix="/organisations", tags=["organisations"])


def _service(db: AsyncSession) -> OrganisationService:
    return OrganisationService(
        OrganisationRepository(db),
        OrganisationMemberRepository(db),
        UserRepository(db),
        AuditService(),
    )


def _bad_request(error: OrganisationError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if error.field == "slug"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(
        status_code=code,
        detail={"message": error.message, "field": error.field},
    )


def _to_response(org: Organisation) -> OrganisationResponse:
    return OrganisationResponse(
        id=org.id,
        slug=org.slug,
        name=org.name,
        description=org.description,
        created_at=org.created_at,
    )


@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organisation",
)
@limiter.limit("30/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
@rate_limit(
    [("user", 20, 3600)],
    limiter_factory=limiter_for,
    on_rejection=audit_on_rejection,
)
async def create_organisation(
    request: Request,
    body: OrganisationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganisationResponse:
    """Create a new organisation with the caller as its sole owner."""
    del request
    try:
        org = await _service(db).create_organisation(
            owner_id=current_user.id,
            slug=body.slug,
            name=body.name,
            description=body.description,
        )
    except OrganisationError as exc:
        raise _bad_request(exc) from exc
    return _to_response(org)


@router.get(
    "",
    response_model=Page[OrganisationResponse],
    status_code=status.HTTP_200_OK,
    summary="List organisations the caller belongs to",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_my_organisations(
    request: Request,
    cursor: str | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[OrganisationResponse]:
    """List the non-deleted organisations the caller is a member of."""
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = OrganisationRepository(db).list_for_user_query(current_user.id)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=Organisation.created_at,
        id_column=Organisation.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[OrganisationResponse](
        items=[_to_response(org) for org in rows],
        next_cursor=next_cursor,
    )


@router.get(
    "/{organisation_id}",
    response_model=OrganisationPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Read the public profile of an organisation",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def get_public_organisation(
    request: Request,
    organisation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OrganisationPublicResponse:
    """Return the public profile of an organisation."""
    del request
    org = await OrganisationRepository(db).get_by_id(organisation_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Organisation not found", "field": "organisation_id"},
        )
    return OrganisationPublicResponse(
        id=org.id, slug=org.slug, name=org.name, description=org.description
    )


@router.post(
    "/{organisation_id}/members",
    response_model=OrganisationMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite an existing user to an organisation",
)
@limiter.limit("30/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def invite_member(
    request: Request,
    organisation_id: uuid.UUID,
    body: OrganisationMemberInviteRequest,
    actor: OrganisationMember = Depends(get_org_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> OrganisationMemberResponse:
    """Add an existing user to an organisation with the requested role."""
    del request
    try:
        member = await _service(db).invite_member(
            actor_id=actor.user_id,
            organisation_id=organisation_id,
            invitee_email=body.email,
            role=body.role,
        )
    except OrganisationError as exc:
        raise _bad_request(exc) from exc
    return OrganisationMemberResponse(
        organisation_id=member.organisation_id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{organisation_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from an organisation",
)
@limiter.limit("30/hour")  # type: ignore[misc]
async def remove_member(
    request: Request,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
    actor: OrganisationMember = Depends(get_org_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a member from an organisation."""
    del request
    try:
        await _service(db).remove_member(
            actor_id=actor.user_id,
            organisation_id=organisation_id,
            member_user_id=user_id,
        )
    except OrganisationError as exc:
        raise _bad_request(exc) from exc
