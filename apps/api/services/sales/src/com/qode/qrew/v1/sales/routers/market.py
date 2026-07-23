import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.database import get_db
from com.qode.qrew.v1.sales.core.dependencies import get_market_service, limiter
from com.qode.qrew.v1.sales.core.principals import AuthenticatedUser, get_current_user
from com.qode.qrew.v1.sales.models.market import MarketAssignment, MarketListing
from com.qode.qrew.v1.sales.schemas.market import (
    MarketAssignmentResponse,
    MarketListingResponse,
    MarketQueueJoinResponse,
    MarketQueueStatusResponse,
    MarketSetHoldersRequest,
)
from com.qode.qrew.v1.sales.services.application.market.service import MarketError, MarketService

logger = structlog.get_logger(__name__)

events_router = APIRouter(prefix="/events", tags=["market"])
tickets_router = APIRouter(prefix="/tickets", tags=["market"])
market_router = APIRouter(prefix="/market", tags=["market"])


def _listing_response(listing: MarketListing) -> MarketListingResponse:
    return MarketListingResponse(
        id=listing.id,
        ticket_id=listing.ticket_id,
        event_id=listing.event_id,
        ticket_type_id=listing.ticket_type_id,
        price_cents=listing.price_cents,
        currency=listing.currency,
        state=listing.state,
        listed_at=listing.listed_at,
        expires_at=listing.expires_at,
        completed_at=listing.completed_at,
        cancelled_at=listing.cancelled_at,
    )


def _assignment_response(
    assignment: MarketAssignment, listing: MarketListing | None = None
) -> MarketAssignmentResponse:
    return MarketAssignmentResponse(
        id=assignment.id,
        listing_id=assignment.listing_id,
        event_id=assignment.event_id,
        price_cents=listing.price_cents if listing else 0,
        currency=listing.currency if listing else "EUR",
        state=assignment.state,
        assigned_at=assignment.assigned_at,
        expires_at=assignment.expires_at,
        holder_name=assignment.holder_name,
        holder_dni=assignment.holder_dni,
    )


def _market_error(exc: MarketError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if exc.field in {"event_id", "ticket_id", "listing_id", "assignment_id", "ticket_type_id"}
        else status.HTTP_409_CONFLICT
        if exc.field in {"state", "user_id"}
        else status.HTTP_410_GONE
        if exc.field == "expires_at"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail={"message": exc.message, "field": exc.field})


# ------------------------------------------------------------------ queue

@events_router.post(
    "/{event_id}/market/queue/join",
    response_model=MarketQueueJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="Join the resale queue for a sold-out event",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def join_market_queue(
    request: Request,
    event_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketQueueJoinResponse:
    del request
    try:
        entry = await service.join_queue(user_id=current_user.id, event_id=event_id)
    except MarketError as exc:
        raise _market_error(exc) from exc
    await db.commit()
    return MarketQueueJoinResponse(in_queue=True, joined_at=entry.joined_at)


@events_router.delete(
    "/{event_id}/market/queue/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave the resale queue for an event",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def leave_market_queue(
    request: Request,
    event_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> None:
    del request
    await service.leave_queue(user_id=current_user.id, event_id=event_id)
    await db.commit()


@events_router.get(
    "/{event_id}/market/queue/status",
    response_model=MarketQueueStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check whether the caller is in the resale queue and if they have a pending assignment",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def market_queue_status(
    request: Request,
    event_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketQueueStatusResponse:
    del request, db
    result = await service.queue_status(user_id=current_user.id, event_id=event_id)
    return MarketQueueStatusResponse(
        in_queue=result["in_queue"],
        joined_at=result["joined_at"],
        pending_assignment_id=result["pending_assignment_id"],
        queue_count=result["queue_count"],
    )


# ------------------------------------------------------------------ listings

@tickets_router.post(
    "/{ticket_id}/market/list",
    response_model=MarketListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="List a ticket for resale on the market",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def list_ticket(
    request: Request,
    ticket_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketListingResponse:
    del request
    try:
        listing = await service.list_ticket(user_id=current_user.id, ticket_id=ticket_id)
    except MarketError as exc:
        raise _market_error(exc) from exc
    await db.commit()
    return _listing_response(listing)


@tickets_router.get(
    "/{ticket_id}/market/listing",
    response_model=MarketListingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the active market listing for a ticket",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_ticket_listing(
    request: Request,
    ticket_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketListingResponse:
    del request, db
    listing = await service.get_listing_for_seller(
        user_id=current_user.id, ticket_id=ticket_id
    )
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No active listing found for this ticket", "field": "ticket_id"},
        )
    return _listing_response(listing)


# ---------------------------------------------------------------- assignments

@market_router.get(
    "/assignments/pending",
    response_model=MarketAssignmentResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get the caller's pending market assignment if any",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_pending_assignment(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketAssignmentResponse | None:
    del request, db
    assignment = await service.get_pending_assignment(user_id=current_user.id)
    if assignment is None:
        return None
    listing = await service._repo.get_listing_by_id(assignment.listing_id)  # noqa: SLF001
    return _assignment_response(assignment, listing)


@market_router.get(
    "/assignments/{assignment_id}",
    response_model=MarketAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific market assignment",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_assignment(
    request: Request,
    assignment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketAssignmentResponse:
    del request, db
    try:
        assignment = await service.get_assignment(
            user_id=current_user.id, assignment_id=assignment_id
        )
    except MarketError as exc:
        raise _market_error(exc) from exc
    listing = await service._repo.get_listing_by_id(assignment.listing_id)  # noqa: SLF001
    return _assignment_response(assignment, listing)


@market_router.put(
    "/assignments/{assignment_id}/holders",
    response_model=MarketAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Set holder name and DNI for the incoming ticket",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def set_assignment_holders(
    request: Request,
    assignment_id: uuid.UUID,
    body: MarketSetHoldersRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> MarketAssignmentResponse:
    del request
    try:
        assignment = await service.set_holders(
            user_id=current_user.id,
            assignment_id=assignment_id,
            holder_name=body.holder_name,
            holder_dni=body.holder_dni,
        )
    except MarketError as exc:
        raise _market_error(exc) from exc
    await db.commit()
    listing = await service._repo.get_listing_by_id(assignment.listing_id)  # noqa: SLF001
    return _assignment_response(assignment, listing)


@market_router.post(
    "/assignments/{assignment_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Decline a market assignment — removes you from the queue",
)
@limiter.limit("10/minute")  # type: ignore[misc]
async def decline_assignment(
    request: Request,
    assignment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> None:
    del request
    try:
        await service.decline_assignment(
            user_id=current_user.id, assignment_id=assignment_id
        )
    except MarketError as exc:
        raise _market_error(exc) from exc
    await db.commit()
