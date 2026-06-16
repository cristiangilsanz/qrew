import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from com.qode.qrew.v1.payments.core.dependencies import (
    get_payment_service,
    get_stripe_client,
    limiter,
)
from com.qode.qrew.v1.payments.core.principals import (
    AuthenticatedUser,
    get_current_user,
)
from com.qode.qrew.v1.payments.schemas.payment import PaymentInitiateResponse
from com.qode.qrew.v1.payments.services import StripeClient
from com.qode.qrew.v1.payments.services.payment import (
    PaymentError,
    PaymentExpiredError,
    PaymentService,
)
from com.qode.qrew.v1.payments.services.webhook_dispatch import dispatch_webhook_event
from com.qode.qrew.v1.payments.services.webhook_idempotency import claim_event

router = APIRouter(tags=["payments"])


@router.post(
    "/reservations/{reservation_id}/payment",
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
        payment = await service.initiate(
            actor_id=current_user.id, reservation_id=reservation_id
        )
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


@router.post(
    "/payments/webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    service: PaymentService = Depends(get_payment_service),
    stripe_client: StripeClient = Depends(get_stripe_client),
) -> dict[str, str]:
    payload = await request.body()
    if stripe_signature is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Missing Stripe-Signature header", "field": None},
        )
    try:
        event = await stripe_client.verify_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid Stripe signature", "field": None},
        ) from exc
    event_id = str(event.get("id") or "")
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Webhook payload missing id", "field": None},
        )
    if not await claim_event(event_id):
        return {"status": "duplicate"}
    await dispatch_webhook_event(service, event)
    return {"status": "ok"}
