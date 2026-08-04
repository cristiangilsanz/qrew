import re
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.sales.core.principals import AuthenticatedUser, get_current_user
from idempotency import idempotent
from com.qode.qrew.v1.sales.core.database import get_db
from com.qode.qrew.v1.sales.core.dependencies import get_reservation_service, limiter
from locking import LockUnavailableError
from com.qode.qrew.v1.sales.models.reservation import Reservation
from com.qode.qrew.v1.sales.models.reservation import ReservationStatus
from com.qode.qrew.v1.sales.models.reservation_holder import ReservationHolder
from com.qode.qrew.v1.sales.repositories.reservation_holder import ReservationHolderRepository
from com.qode.qrew.v1.sales.schemas.reservation import (
    HolderResponse,
    ReservationCreateRequest,
    ReservationResponse,
    SetHoldersRequest,
)
from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.sales.services.application.reservation import (
    FraudBlockedError,
    ReservationError,
    ReservationService,
    TierBusyError,
)
from com.qode.qrew.v1.sales.core.config import settings

logger = structlog.get_logger(__name__)

_FINGERPRINT_RE = re.compile(r"^[0-9a-fA-F]{32,128}$")

events_router = APIRouter(prefix="/events", tags=["reservations"])
router = APIRouter(prefix="/reservations", tags=["reservations"])


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
        else status.HTTP_403_FORBIDDEN
        if error.field == "reservation_window_token"
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(
        status_code=code,
        detail={"message": error.message, "field": error.field},
    )


@events_router.post(
    "/{event_id}/reserve",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve tickets against an event under the per-user limit",
)
@limiter.limit("30/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=300)
async def create_reservation(
    request: Request,
    event_id: uuid.UUID,
    body: ReservationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    client_host = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and settings.trusted_proxy_ip and client_host == settings.trusted_proxy_ip:
        ip_address: str | None = forwarded.split(",", 1)[0].strip()
    else:
        ip_address = client_host
    raw_fp = request.headers.get("X-Device-Fingerprint")
    fingerprint = raw_fp if raw_fp and _FINGERPRINT_RE.match(raw_fp) else None

    try:
        reservation = await service.reserve(
            user_id=current_user.id,
            event_id=event_id,
            ticket_type_id=body.ticket_type_id,
            quantity=body.quantity,
            ip_address=ip_address,
            fingerprint_hash=fingerprint,
            reservation_window_token=body.reservation_window_token,
        )
    except FraudBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Reservation rejected for risk", "field": None},
        ) from exc
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

    return _to_response(reservation)


@router.post(
    "/{reservation_id}/cancel",
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
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    del request
    try:
        reservation = await service.cancel(actor_id=current_user.id, reservation_id=reservation_id)
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
    "/{reservation_id}",
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
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    del request
    try:
        reservation = await service.get_for_user(
            actor_id=current_user.id, reservation_id=reservation_id
        )
    except ReservationError as exc:
        raise _bad_request(exc) from exc
    return _to_response(reservation)


@router.put(
    "/{reservation_id}/holders",
    response_model=list[HolderResponse],
    status_code=status.HTTP_200_OK,
    summary="Set holder info (name + DNI) for each ticket slot in a reservation",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def set_holders(
    request: Request,
    reservation_id: uuid.UUID,
    body: SetHoldersRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HolderResponse]:
    del request
    reservation = await ReservationRepository(db).get_by_id(reservation_id)
    if reservation is None or reservation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Reservation not found", "field": "reservation_id"},
        )
    if reservation.status != ReservationStatus.reserved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Reservation is no longer modifiable", "field": "status"},
        )
    if len(body.holders) != reservation.quantity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": f"Expected {reservation.quantity} holder(s)", "field": "holders"},
        )
    positions = sorted(h.position for h in body.holders)
    if positions != list(range(1, reservation.quantity + 1)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Positions must be 1..quantity with no gaps", "field": "holders"},
        )
    holder_models = [
        ReservationHolder(
            reservation_id=reservation_id,
            position=h.position,
            holder_name=h.holder_name,
            holder_dni=h.holder_dni,
        )
        for h in body.holders
    ]
    await ReservationHolderRepository(db).upsert_all(reservation_id, holder_models)
    await db.commit()
    return [
        HolderResponse(position=h.position, holder_name=h.holder_name, holder_dni=h.holder_dni)
        for h in body.holders
    ]
