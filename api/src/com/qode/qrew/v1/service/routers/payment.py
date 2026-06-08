import uuid
from typing import Any, cast

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth.auth import get_current_user
from com.qode.qrew.v1.service.core.idempotency import idempotent
from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.core.infra.limiter import limiter
from com.qode.qrew.v1.service.core.locking.errors import LockUnavailableError
from com.qode.qrew.v1.service.core.payments import StripeClient, StripeRealClient
from com.qode.qrew.v1.service.core.payments.webhook_idempotency import claim_event
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.repositories.payment import PaymentRepository
from com.qode.qrew.v1.service.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.service.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.service.schemas.payment import PaymentInitiateResponse
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.payment import (
    PaymentError,
    PaymentExpiredError,
    PaymentService,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["payments"])

_stripe_client: StripeClient = StripeRealClient()


def get_stripe_client() -> StripeClient:
    """FastAPI dependency override seam for tests."""
    return _stripe_client


def _service(db: AsyncSession, stripe: StripeClient) -> PaymentService:
    return PaymentService(
        db,
        PaymentRepository(db),
        ReservationRepository(db),
        TicketTypeRepository(db),
        stripe,
        AuditService(),
    )


@router.post(
    "/reservations/{reservation_id}/payment",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or return the PaymentIntent for a reservation",
)
@limiter.limit("30/minute")  # type: ignore[misc]
@idempotent(scope="user", ttl_seconds=600)
async def initiate_payment(
    request: Request,
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    stripe_client: StripeClient = Depends(get_stripe_client),
) -> PaymentInitiateResponse:
    """Initiate a PaymentIntent for the caller's reservation."""
    del request
    service = _service(db, stripe_client)
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
    db: AsyncSession = Depends(get_db),
    stripe_client: StripeClient = Depends(get_stripe_client),
) -> dict[str, str]:
    """Stripe-Signature-verified webhook entry point."""
    payload = await request.body()
    audit = AuditService()
    if stripe_signature is None:
        try:
            await audit.record(
                action=AuditAction.WEBHOOK_INVALID_SIGNATURE,
                actor_id=None,
                entity_type="payment",
                entity_id=None,
                payload={"reason": "missing_signature"},
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Missing Stripe-Signature header", "field": None},
        )
    try:
        event = stripe_client.verify_webhook(payload, stripe_signature)
    except Exception as exc:
        try:
            await audit.record(
                action=AuditAction.WEBHOOK_INVALID_SIGNATURE,
                actor_id=None,
                entity_type="payment",
                entity_id=None,
                payload={"reason": "verification_failed"},
            )
        except Exception:
            pass
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
    await _dispatch_event(_service(db, stripe_client), event)
    return {"status": "ok"}


def _read_str(d: dict[str, Any], key: str) -> str | None:
    value: Any = d.get(key)
    return value if isinstance(value, str) else None


def _read_dict(d: dict[str, Any], key: str) -> dict[str, Any]:
    value: Any = d.get(key)
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _read_int(d: dict[str, Any], key: str) -> int | None:
    value: Any = d.get(key)
    return value if isinstance(value, int) else None


async def _dispatch_event(service: PaymentService, event: dict[str, Any]) -> None:
    event_type = _read_str(event, "type") or ""
    data_section = _read_dict(event, "data")
    data_object = _read_dict(data_section, "object")
    intent_id = _payment_intent_id_for(event_type, data_object)
    if intent_id is None:
        return
    try:
        if event_type == "payment_intent.succeeded":
            await service.apply_succeeded(intent_id=intent_id)
        elif event_type == "payment_intent.payment_failed":
            last_error = _read_dict(data_object, "last_payment_error")
            await service.apply_failed(
                intent_id=intent_id,
                failure_code=_read_str(last_error, "code"),
                failure_message=_read_str(last_error, "message"),
            )
        elif event_type in {
            "payment_intent.requires_action",
            "payment_intent.processing",
        }:
            stripe_status = _read_str(data_object, "status")
            if stripe_status is not None:
                await service.update_intermediate(
                    intent_id=intent_id, status=stripe_status
                )
        elif event_type == "charge.refunded":
            amount = _read_int(data_object, "amount") or 0
            amount_refunded = _read_int(data_object, "amount_refunded") or 0
            await service.apply_refund(
                intent_id=intent_id,
                amount_refunded=amount_refunded,
                amount_total=amount,
            )
        elif event_type == "charge.dispute.created":
            await service.apply_chargeback(intent_id=intent_id)
        elif event_type == "charge.dispute.closed":
            await service.record_chargeback_closed(intent_id=intent_id)
    except LockUnavailableError:
        await logger.awarning(
            "webhook_lock_unavailable", event_type=event_type, intent_id=intent_id
        )


def _payment_intent_id_for(event_type: str, data_object: dict[str, Any]) -> str | None:
    """Charge events carry the intent id on payment_intent; intent events on id."""
    if event_type.startswith("charge."):
        return _read_str(data_object, "payment_intent")
    return _read_str(data_object, "id")
