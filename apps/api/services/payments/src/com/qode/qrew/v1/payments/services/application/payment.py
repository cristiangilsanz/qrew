# creates payment intents from reservations and market assignments and applies stripe outcomes
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from observability import traced
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.payments.core.config import settings
from com.qode.qrew.v1.payments.core.errors import DomainError
from com.qode.qrew.v1.payments.core.utils import crypto as pii_crypto
from outbox import record as record_event

from com.qode.qrew.v1.payments.models.outbox import EventOutbox
from com.qode.qrew.v1.payments.models.payment import Payment, PaymentStatus
from com.qode.qrew.v1.payments.repositories.payment import PaymentRepository
from com.qode.qrew.v1.payments.services.application.stripe_client import StripeClient
from com.qode.qrew.v1.payments.services.domain.status import is_terminal, map_intent_status

logger = structlog.get_logger(__name__)


class PaymentError(DomainError):
    pass


class PaymentExpiredError(DomainError):
    pass


class WebhookError(Exception):
    # stores the message describing the webhook failure
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class _ReservationContext:
    amount_cents: int
    currency: str
    is_valid: bool
    error_code: str | None = None


# asks sales whether a market assignment can be charged and for how much
async def _get_assignment_context(
    assignment_id: uuid.UUID, user_id: uuid.UUID
) -> _ReservationContext:
    async with httpx.AsyncClient(base_url=settings.sales_url) as client:
        resp = await client.post(
            f"/v1/billing/market-assignments/{assignment_id}/charge",
            json={"user_id": str(user_id)},
            headers={"X-Internal-Key": settings.internal_api_key},
            timeout=5.0,
        )
    if resp.status_code == 200:  # noqa: PLR2004
        data = resp.json()
        return _ReservationContext(
            amount_cents=data["amount_cents"],
            currency=data["currency"],
            is_valid=True,
        )
    if resp.status_code in (400, 404, 410):
        data = resp.json()
        return _ReservationContext(
            amount_cents=0,
            currency="",
            is_valid=False,
            error_code=data.get("error_code") or str(resp.status_code),
        )
    resp.raise_for_status()
    return _ReservationContext(amount_cents=0, currency="", is_valid=False, error_code="unknown")


# asks sales whether a reservation can be charged and for how much
async def _get_reservation_context(
    reservation_id: uuid.UUID, user_id: uuid.UUID
) -> _ReservationContext:
    async with httpx.AsyncClient(base_url=settings.sales_url) as client:
        resp = await client.post(
            f"/v1/billing/reservations/{reservation_id}/charge",
            json={"user_id": str(user_id)},
            headers={"X-Internal-Key": settings.internal_api_key},
            timeout=5.0,
        )
    if resp.status_code == 200:  # noqa: PLR2004
        data = resp.json()
        return _ReservationContext(
            amount_cents=data["amount_cents"],
            currency=data["currency"],
            is_valid=True,
        )
    if resp.status_code in (404, 400, 410):
        data = resp.json()
        return _ReservationContext(
            amount_cents=0,
            currency="",
            is_valid=False,
            error_code=data.get("error_code") or str(resp.status_code),
        )
    resp.raise_for_status()
    return _ReservationContext(amount_cents=0, currency="", is_valid=False, error_code="unknown")


# collects the identifiers a payment actually carries, omitting the ones it has none of
def _payment_scope(payment: Payment) -> dict[str, Any]:
    scope: dict[str, Any] = {"payment_id": str(payment.id)}
    if payment.reservation_id is not None:
        scope["reservation_id"] = str(payment.reservation_id)
    if payment.market_assignment_id is not None:
        scope["market_assignment_id"] = str(payment.market_assignment_id)
    if payment.user_id is not None:
        scope["user_id"] = str(payment.user_id)
    return scope


# publishes a payment event onto the shared nats connection
async def _publish_event(
    session: AsyncSession,
    subject: str,
    data: dict[str, Any],
    *,
    actor_id: uuid.UUID | None = None,
) -> None:
    await record_event(
        session,
        EventOutbox,
        subject=subject,
        aggregate_type="payment",
        aggregate_id=str(data.get("payment_id", "")),
        data=data,
        actor_id=str(actor_id) if actor_id else None,
    )


class PaymentService:
    # stores the session repository and stripe client the service uses
    def __init__(
        self,
        session: AsyncSession,
        repo: PaymentRepository,
        stripe: StripeClient,
    ) -> None:
        self._session = session
        self._repo = repo
        self._stripe = stripe

    # creates or returns the payment intent for a market assignment
    @traced("payment.initiate_for_assignment")
    async def initiate_for_assignment(
        self, *, actor_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> Payment:
        ctx = await _get_assignment_context(assignment_id, actor_id)
        if not ctx.is_valid:
            if ctx.error_code in ("410", "expires_at"):
                raise PaymentExpiredError("Assignment expired.", field="expires_at")
            if ctx.error_code in ("404", "assignment_id"):
                raise PaymentError("Assignment not found.", field="assignment_id")
            raise PaymentError("Assignment not ready for payment.", field="state")

        existing = await self._repo.get_by_assignment_id(assignment_id)
        if existing is not None and existing.provider_payment_intent_id:
            return existing

        payment = existing or Payment(
            id=uuid.uuid4(),
            reservation_id=None,
            market_assignment_id=assignment_id,
            user_id=actor_id,
            amount_cents=ctx.amount_cents,
            currency=ctx.currency,
        )
        intent = await self._stripe.create_payment_intent(
            amount_cents=ctx.amount_cents,
            currency=ctx.currency,
            idempotency_key=f"market_assignment:{assignment_id}:{payment.id}",
            metadata={"market_assignment_id": str(assignment_id)},
        )
        payment.provider_payment_intent_id = intent.intent_id
        payment.client_secret_ciphertext = pii_crypto.encrypt(intent.client_secret)
        payment.status = map_intent_status(intent.status)
        if existing is None:
            payment = await self._repo.insert(payment)
        else:
            await self._repo.flush()

        await _publish_event(
            self._session,
            "payments.payment.initiated.v1",
            {
                "payment_id": str(payment.id),
                "market_assignment_id": str(assignment_id),
                "user_id": str(actor_id),
                "amount_cents": ctx.amount_cents,
                "currency": ctx.currency,
            },
            actor_id=actor_id,
        )
        return payment

    # creates or returns the payment intent for a reservation
    @traced("payment.initiate")
    async def initiate(self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID) -> Payment:
        ctx = await _get_reservation_context(reservation_id, actor_id)
        if not ctx.is_valid:
            if ctx.error_code in ("410", "expired"):
                raise PaymentExpiredError("Reservation expired.", field="expires_at")
            if ctx.error_code in ("404", "not_found", "wrong_owner"):
                raise PaymentError("Reservation not found.", field="reservation_id")
            raise PaymentError("Reservation not pending payment.", field="status")

        existing = await self._repo.get_by_reservation_id(reservation_id)
        if existing is not None and existing.provider_payment_intent_id:
            return existing

        payment = existing or Payment(
            id=uuid.uuid4(),
            reservation_id=reservation_id,
            user_id=actor_id,
            amount_cents=ctx.amount_cents,
            currency=ctx.currency,
        )
        intent = await self._stripe.create_payment_intent(
            amount_cents=ctx.amount_cents,
            currency=ctx.currency,
            idempotency_key=f"reservation:{reservation_id}:{payment.id}",
            metadata={"reservation_id": str(reservation_id)},
        )
        payment.provider_payment_intent_id = intent.intent_id
        payment.client_secret_ciphertext = pii_crypto.encrypt(intent.client_secret)
        payment.status = map_intent_status(intent.status)
        if existing is None:
            payment = await self._repo.insert(payment)
        else:
            await self._repo.flush()

        await _publish_event(
            self._session,
            "payments.payment.initiated.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(reservation_id),
                "user_id": str(actor_id),
                "amount_cents": ctx.amount_cents,
                "currency": ctx.currency,
            },
            actor_id=actor_id,
        )
        return payment

    # decrypts the stored client secret of a payment
    def decrypt_client_secret(self, payment: Payment) -> str | None:
        if payment.client_secret_ciphertext is None:
            return None
        return pii_crypto.decrypt(payment.client_secret_ciphertext)

    # marks a payment as succeeded and publishes the outcome
    @traced("payment.apply_succeeded")
    async def apply_succeeded(self, *, intent_id: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            await logger.awarning("payment_intent_unknown", intent_id=intent_id)
            return
        payment.status = PaymentStatus.succeeded
        await self._repo.flush()

        data = _payment_scope(payment)
        if payment.market_assignment_id is not None:
            data["payment_intent_id"] = intent_id
        await _publish_event(self._session, "payments.payment.succeeded.v1", data)

    # marks a payment as failed and publishes the outcome
    @traced("payment.apply_failed")
    async def apply_failed(
        self,
        *,
        intent_id: str,
        failure_code: str | None,
        failure_message: str | None,
    ) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        payment.status = PaymentStatus.failed
        payment.failure_code = failure_code
        payment.failure_message = failure_message
        await self._repo.flush()
        await _publish_event(
            self._session,
            "payments.payment.failed.v1",
            {
                **_payment_scope(payment),
                "failure_code": failure_code,
                "failure_message": failure_message,
            },
        )

    # marks a payment as refunded when the refund covers the full amount
    @traced("payment.apply_refund")
    async def apply_refund(
        self, *, intent_id: str, amount_refunded: int, amount_total: int
    ) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        is_full_refund = amount_refunded >= amount_total
        if is_full_refund:
            payment.status = PaymentStatus.refunded
            await self._repo.flush()
        await _publish_event(
            self._session,
            "payments.payment.refunded.v1",
            {
                **_payment_scope(payment),
                "amount_refunded_cents": amount_refunded,
                "amount_total_cents": amount_total,
                "is_full_refund": is_full_refund,
            },
        )

    # marks a payment as refunded when a chargeback opens against it
    @traced("payment.apply_chargeback")
    async def apply_chargeback(self, *, intent_id: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        payment.status = PaymentStatus.refunded
        await self._repo.flush()
        await _publish_event(
            self._session,
            "payments.chargeback.opened.v1",
            _payment_scope(payment),
        )

    # publishes that a chargeback has closed
    @traced("payment.record_chargeback_closed")
    async def record_chargeback_closed(self, *, intent_id: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        await _publish_event(
            self._session,
            "payments.chargeback.closed.v1",
            _payment_scope(payment),
        )

    # updates a payment to a non final stripe status
    async def update_intermediate(self, *, intent_id: str, status: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        new_status = map_intent_status(status)
        if is_terminal(new_status):
            return
        payment.status = new_status
        await self._repo.flush()

    # verifies and dispatches an incoming stripe webhook event
    async def handle_webhook(self, payload: bytes, signature: str | None) -> dict[str, str]:
        from com.qode.qrew.v1.payments.services.application.webhooks.dispatch import (
            dispatch_webhook_event,
        )
        from com.qode.qrew.v1.payments.services.application.webhooks.idempotency import (
            claim_event,
        )

        if signature is None:
            raise WebhookError("Stripe signature missing.")
        try:
            event = await self._stripe.verify_webhook(payload, signature)
        except Exception as exc:
            raise WebhookError("Stripe signature rejected.") from exc
        event_id = str(event.get("id") or "")
        if not event_id:
            raise WebhookError("Webhook payload rejected.")
        if not await claim_event(event_id):
            return {"status": "duplicate"}
        await dispatch_webhook_event(self, event)
        return {"status": "ok"}
