import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.catalog.routers import Page, clamp_limit, cursor_paginate
from com.qode.qrew.v1.catalog.core.dependencies import get_event_member
from com.qode.qrew.v1.catalog.services.audit import AuditService
from idempotency import idempotent
from com.qode.qrew.v1.catalog.core.database import get_db
from com.qode.qrew.v1.catalog.core.dependencies import limiter
from locking import LockUnavailableError
from com.qode.qrew.v1.catalog.models.organisation import OrganisationMember, OrganisationRole
from com.qode.qrew.v1.catalog.models.ticket_type import TicketType
from com.qode.qrew.v1.catalog.repositories.event import EventRepository
from com.qode.qrew.v1.catalog.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.catalog.schemas.ticket_type import (
    TicketTypeCreateRequest,
    TicketTypeResponse,
    TicketTypeUpdateRequest,
)
from com.qode.qrew.v1.catalog.services.ticket_type import (
    TicketTypeError,
    TicketTypeService,
)

router = APIRouter(prefix="/events/{event_id}/ticket-types", tags=["ticket-types"])


def _service(db: AsyncSession) -> TicketTypeService:
    return TicketTypeService(EventRepository(db), TicketTypeRepository(db), AuditService())


def _to_response(ticket_type: TicketType) -> TicketTypeResponse:
    return TicketTypeResponse(
        id=ticket_type.id,
        event_id=ticket_type.event_id,
        name=ticket_type.name,
        description=ticket_type.description,
        capacity=ticket_type.capacity,
        reserved_count=ticket_type.reserved_count,
        available=ticket_type.capacity - ticket_type.reserved_count,
        price_cents=ticket_type.price_cents,
        currency=ticket_type.currency,
        position=ticket_type.position,
        created_at=ticket_type.created_at,
    )


def _domain_to_http(error: TicketTypeError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"event_id", "ticket_type_id"}
        else status.HTTP_409_CONFLICT
        if error.field == "name"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail={"message": error.message, "field": error.field})


@router.post(
    "",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket type under an event",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def create_ticket_type(
    request: Request,
    event_id: uuid.UUID,
    body: TicketTypeCreateRequest,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> TicketTypeResponse:
    del request
    try:
        ticket_type = await _service(db).create(
            actor_id=actor.user_id,
            event_id=event_id,
            name=body.name,
            description=body.description,
            capacity=body.capacity,
            price_cents=body.price_cents,
            currency=body.currency,
            position=body.position,
        )
    except TicketTypeError as exc:
        raise _domain_to_http(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another ticket-type change is in progress", "field": None},
        ) from exc
    return _to_response(ticket_type)


@router.patch(
    "/{ticket_type_id}",
    response_model=TicketTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a ticket type",
)
@limiter.limit("60/hour")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def update_ticket_type(
    request: Request,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    body: TicketTypeUpdateRequest,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> TicketTypeResponse:
    del request
    changes = body.model_dump(exclude_unset=True)
    try:
        ticket_type = await _service(db).update(
            actor_id=actor.user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            changes=changes,
        )
    except TicketTypeError as exc:
        raise _domain_to_http(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another ticket-type change is in progress", "field": None},
        ) from exc
    return _to_response(ticket_type)


@router.delete(
    "/{ticket_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a ticket type",
)
@limiter.limit("60/hour")  # type: ignore[misc]
async def delete_ticket_type(
    request: Request,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    actor: OrganisationMember = Depends(get_event_member(OrganisationRole.manager)),
    db: AsyncSession = Depends(get_db),
) -> None:
    del request
    try:
        await _service(db).delete(
            actor_id=actor.user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
        )
    except TicketTypeError as exc:
        raise _domain_to_http(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Another ticket-type change is in progress", "field": None},
        ) from exc


@router.get(
    "",
    response_model=Page[TicketTypeResponse],
    status_code=status.HTTP_200_OK,
    summary="List ticket types for an event",
)
@limiter.limit("120/minute")  # type: ignore[misc]
async def list_ticket_types(
    request: Request,
    event_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> Page[TicketTypeResponse]:
    del request
    page_limit = clamp_limit(limit, default=20)
    stmt = _service(db).list_for_event_query(event_id)
    rows, next_cursor = await cursor_paginate(
        db,
        stmt,
        sort_column=TicketType.position,
        id_column=TicketType.id,
        limit=page_limit,
        cursor=cursor,
    )
    return Page[TicketTypeResponse](
        items=[_to_response(row) for row in rows], next_cursor=next_cursor
    )
