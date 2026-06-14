import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.services.audit import AuditService
from com.qode.qrew.v1.sales.services.auth.auth import AuthenticatedUser, get_current_user
from idempotency import idempotent
from com.qode.qrew.v1.sales.database import get_db
from com.qode.qrew.v1.sales.services.infra.limiter import limiter
from com.qode.qrew.v1.sales.repositories.projections import EventContextRepository
from com.qode.qrew.v1.sales.schemas.queue import (
    QueueJoinResponse,
    QueuePositionResponse,
    QueueRedeemRequest,
    QueueRedeemResponse,
)
from com.qode.qrew.v1.sales.services.queue.queue import QueueError, QueueService

router = APIRouter(prefix="/events/{event_id}/queue", tags=["queue"])


def _service(db: AsyncSession) -> QueueService:
    return QueueService(EventContextRepository(db), AuditService())


def _bad_request(error: QueueError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field == "event_id"
        else status.HTTP_409_CONFLICT
        if error.field in {"sale_starts_at", "sale_window", "queue_required"}
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(
        status_code=code, detail={"message": error.message, "field": error.field}
    )


@router.post(
    "/join",
    response_model=QueueJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="Join the virtual waiting room for an event",
)
@limiter.limit("10/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=60)
async def join_queue_endpoint(
    request: Request,
    event_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueJoinResponse:
    del request
    tiebreak = secrets.randbits(16)
    try:
        position = await _service(db).join(
            user_id=current_user.id, event_id=event_id, tiebreak=tiebreak
        )
    except QueueError as exc:
        raise _bad_request(exc) from exc
    return QueueJoinResponse(position=position)


@router.get(
    "/position",
    response_model=QueuePositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Read the caller's current queue position",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def queue_position_endpoint(
    request: Request,
    event_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueuePositionResponse:
    del request
    position = await _service(db).position(user_id=current_user.id, event_id=event_id)
    return QueuePositionResponse(position=position)


@router.post(
    "/redeem",
    response_model=QueueRedeemResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a redeem token for a reservation window",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def redeem_queue_endpoint(
    request: Request,
    event_id: uuid.UUID,
    body: QueueRedeemRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueRedeemResponse:
    del request
    del event_id
    try:
        reservation_token = await _service(db).redeem(
            user_id=current_user.id, token=body.redeem_window_token
        )
    except QueueError as exc:
        raise _bad_request(exc) from exc
    return QueueRedeemResponse(reservation_window_token=reservation_token)
