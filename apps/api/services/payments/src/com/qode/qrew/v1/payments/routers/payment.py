import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from com.qode.qrew.v1.payments.core.dependencies import (
    get_payment_service,
    limiter,
)
from com.qode.qrew.v1.payments.core.principals import (
    AuthenticatedUser,
    get_current_user,
)
from com.qode.qrew.v1.payments.schemas.payment import PaymentInitiateResponse
from com.qode.qrew.v1.payments.services.application.payment import (
    PaymentError,
    PaymentExpiredError,
    PaymentService,
    WebhookError,
)

router = APIRouter(prefix="/reservations", tags=["payments"])
market_router = APIRouter(prefix="/market-assignments", tags=["payments"])
webhooks_router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/{reservation_id}/payment",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or return the PaymentIntent for a reservation",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def initiate_payment(
    request: Request,
    reservation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentInitiateResponse:
    del request
    try:
        payment = await service.initiate(actor_id=current_user.id, reservation_id=reservation_id)
    except PaymentExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    except PaymentError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.field in {"reservation_id", "ticket_type_id"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=code,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    client_secret = service.decrypt_client_secret(payment) or ""
    return PaymentInitiateResponse(
        id=payment.id,
        reservation_id=payment.reservation_id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        status=payment.status,
        client_secret=client_secret,
        created_at=payment.created_at,
    )


@market_router.post(
    "/{assignment_id}/payment",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or return the PaymentIntent for a market assignment",
)
@limiter.limit("30/minute")  # type: ignore[misc]
async def initiate_assignment_payment(
    request: Request,
    assignment_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentInitiateResponse:
    del request
    try:
        payment = await service.initiate_for_assignment(
            actor_id=current_user.id, assignment_id=assignment_id
        )
    except PaymentExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    except PaymentError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.field == "assignment_id"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=code,
            detail={"message": exc.message, "field": exc.field},
        ) from exc
    client_secret = service.decrypt_client_secret(payment) or ""
    return PaymentInitiateResponse(
        id=payment.id,
        reservation_id=payment.reservation_id or payment.market_assignment_id or payment.id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        status=payment.status,
        client_secret=client_secret,
        created_at=payment.created_at,
    )


@webhooks_router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    service: PaymentService = Depends(get_payment_service),
) -> dict[str, str]:
    payload = await request.body()
    try:
        return await service.handle_webhook(payload, stripe_signature)
    except WebhookError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "field": None},
        ) from exc
