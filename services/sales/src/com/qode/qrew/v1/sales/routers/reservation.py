import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.services.audit import AuditService
from com.qode.qrew.v1.sales.core.principals import AuthenticatedUser, get_current_user
from idempotency import idempotent
from com.qode.qrew.v1.sales.core.database import get_db
from com.qode.qrew.v1.sales.core.dependencies import limiter
from locking import LockUnavailableError
from com.qode.qrew.v1.sales.services.queue.redis_queue import consume_reservation_token
from com.qode.qrew.v1.sales.models.reservation import Reservation
from com.qode.qrew.v1.sales.repositories.projections import (
    EventContextRepository,
    TicketTypeInventoryRepository,
)
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.schemas.reservation import (
    ReservationCreateRequest,
    ReservationResponse,
)
from com.qode.qrew.v1.sales.services.fraud.context import PurchaseContext
from com.qode.qrew.v1.sales.services.fraud.dependencies import build_engine_for_user
from com.qode.qrew.v1.sales.services.fraud.engine import FraudDecision
from com.qode.qrew.v1.sales.services.reservation.reservation import (
    ReservationError,
    ReservationService,
    TierBusyError,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["reservations"])


def _make_service(db: AsyncSession) -> ReservationService:
    return ReservationService(
        db,
        ReservationRepository(db),
        EventContextRepository(db),
        TicketTypeInventoryRepository(db),
        AuditService(),
    )


def _to_response(reservation: Reservation) -> ReservationResponse:
    return ReservationResponse(
        id=reservation.id,
        event_id=reservation.event_id,
        ticket_type_id=reservation.ticket_type_id,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
    )


def _bad_request(error: ReservationError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.field in {"event_id", "reservation_id", "ticket_type_id"}
        else status.HTTP_409_CONFLICT
        if error.field == "quantity"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(
        status_code=code,
        detail={"message": error.message, "field": error.field},
    )


@router.post(
    "/events/{event_id}/reserve",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve tickets against an event under the per-user limit",
)
@limiter.limit("30/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def reserve_event(
    request: Request,
    event_id: uuid.UUID,
    body: ReservationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address: str | None = forwarded.split(",", 1)[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    fingerprint = request.headers.get("X-Device-Fingerprint")

    engine = await build_engine_for_user(db, user_id=current_user.id, fingerprint_hash=fingerprint)
    fraud_context = PurchaseContext(
        user_id=current_user.id,
        ip_address=ip_address,
        device_fingerprint_hash=fingerprint,
        now=datetime.now(UTC),
    )
    evaluation = await engine.evaluate(fraud_context)
    service = _make_service(db)

    if evaluation.decision == FraudDecision.block:
        await service.record_blocked(
            actor_id=current_user.id,
            event_id=event_id,
            payload=evaluation.to_payload(),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Reservation rejected for risk", "field": None},
        )

    event_ctx = await service.get_event_context(event_id)
    if event_ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Event not found", "field": "event_id"},
        )

    if event_ctx.queue_required:
        if body.reservation_window_token is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Reservation window token is required for this event",
                    "field": "reservation_window_token",
                },
            )
        try:
            token_event = await consume_reservation_token(
                token=body.reservation_window_token, user_id=current_user.id
            )
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Reservation window token is invalid",
                    "field": "reservation_window_token",
                },
            ) from exc
        if token_event != event_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Reservation window token is for a different event",
                    "field": "reservation_window_token",
                },
            )
        try:
            reservation = await service.reserve_with_queue_token(
                user_id=current_user.id,
                event_id=event_id,
                ticket_type_id=body.ticket_type_id,
                quantity=body.quantity,
                risk_score=evaluation.score,
                requires_review=evaluation.decision == FraudDecision.review,
            )
        except ReservationError as exc:
            raise _bad_request(exc) from exc
        except TierBusyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Ticket type is being purchased by another caller",
                    "field": "ticket_type_id",
                },
            ) from exc
        except LockUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Another reservation by this user is in progress",
                    "field": None,
                },
            ) from exc
    else:
        try:
            reservation = await service.reserve(
                user_id=current_user.id,
                event_id=event_id,
                ticket_type_id=body.ticket_type_id,
                quantity=body.quantity,
                risk_score=evaluation.score,
                requires_review=evaluation.decision == FraudDecision.review,
            )
        except ReservationError as exc:
            raise _bad_request(exc) from exc
        except TierBusyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Ticket type is being purchased by another caller",
                    "field": "ticket_type_id",
                },
            ) from exc
        except LockUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Another reservation by this user is in progress",
                    "field": None,
                },
            ) from exc

    if evaluation.decision == FraudDecision.review:
        await service.record_flagged(
            actor_id=current_user.id,
            reservation_id=reservation.id,
            payload=evaluation.to_payload(),
        )

    return _to_response(reservation)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an open reservation",
)
@limiter.limit("30/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def cancel_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    del request
    try:
        reservation = await _make_service(db).cancel(
            actor_id=current_user.id, reservation_id=reservation_id
        )
    except ReservationError as exc:
        raise _bad_request(exc) from exc
    except LockUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Another lifecycle change is in progress",
                "field": None,
            },
        ) from exc
    return _to_response(reservation)


@router.get(
    "/reservations/{reservation_id}",
    response_model=ReservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a reservation owned by the caller",
)
@limiter.limit("60/minute")  # type: ignore[misc]
async def get_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservationResponse:
    del request
    try:
        reservation = await _make_service(db).get_for_user(
            actor_id=current_user.id, reservation_id=reservation_id
        )
    except ReservationError as exc:
        raise _bad_request(exc) from exc
    return _to_response(reservation)
