# exposes the endpoints for the resale market's queue listings and assignments
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
    MarketQueueEntryResponse,
    MarketQueueJoinResponse,
    MarketQueueStatusResponse,
    MarketSetHoldersRequest,
)
from com.qode.qrew.v1.sales.services.application.market.service import MarketError, MarketService

logger = structlog.get_logger(__name__)

events_router = APIRouter(prefix="/events", tags=["market"])
tickets_router = APIRouter(prefix="/tickets", tags=["market"])
market_router = APIRouter(prefix="/market", tags=["market"])


# converts a listing into its response
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


# converts an assignment into its response with its listing's pricing
def _assignment_response(
    assignment: MarketAssignment, listing: MarketListing | None = None
) -> MarketAssignmentResponse:
    return MarketAssignmentResponse(
        id=assignment.id,
        listing_id=assignment.listing_id,
        event_id=assignment.event_id,
        ticket_type_id=listing.ticket_type_id if listing else None,
        price_cents=listing.price_cents if listing else 0,
        currency=listing.currency if listing else "EUR",
        state=assignment.state,
        assigned_at=assignment.assigned_at,
        expires_at=assignment.expires_at,
        holder_name=assignment.holder_name,
        holder_dni=assignment.holder_dni,
    )


# converts a market error into its http response
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


# joins the caller into an event's resale queue
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


# removes the caller from an event's resale queue
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


# reports the caller's resale queue standing and any pending assignment
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


# lists a ticket for resale on the market
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


# reads a ticket's active listing
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
    listing = await service.get_listing_for_seller(user_id=current_user.id, ticket_id=ticket_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Listing not found.", "field": "ticket_id"},
        )
    return _listing_response(listing)


# lists every resale queue the caller is active in
@market_router.get(
    "/queues",
    response_model=list[MarketQueueEntryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all active resale queue entries for the caller",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_my_queues(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> list[MarketQueueEntryResponse]:
    del request, db
    entries = await service.my_queues(user_id=current_user.id)
    return [MarketQueueEntryResponse(**e) for e in entries]


# lists the caller's pending assignments and the ones that ended recently
@market_router.get(
    "/assignments",
    response_model=list[MarketAssignmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List the caller's pending and recently ended market assignments",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def list_assignments(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> list[MarketAssignmentResponse]:
    del request, db
    assignments = await service.list_recent_assignments(user_id=current_user.id)
    responses: list[MarketAssignmentResponse] = []
    for assignment in assignments:
        listing = await service.get_listing(listing_id=assignment.listing_id)
        responses.append(_assignment_response(assignment, listing))
    return responses


# reads the caller's pending market assignment if any
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
    listing = await service.get_listing(listing_id=assignment.listing_id)
    return _assignment_response(assignment, listing)


# reads a specific market assignment owned by the caller
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
    listing = await service.get_listing(listing_id=assignment.listing_id)
    return _assignment_response(assignment, listing)


# names the holder of the ticket an assignment will transfer
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
    listing = await service.get_listing(listing_id=assignment.listing_id)
    await db.commit()
    return _assignment_response(assignment, listing)


# declines a market assignment and removes the caller from the queue
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
        await service.decline_assignment(user_id=current_user.id, assignment_id=assignment_id)
    except MarketError as exc:
        raise _market_error(exc) from exc
    await db.commit()
