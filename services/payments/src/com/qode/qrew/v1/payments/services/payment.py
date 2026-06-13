"""Payment service — owns Stripe lifecycle, publishes saga events to NATS."""
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.payments.core.auth import pii_crypto
from com.qode.qrew.v1.payments.core.infra.errors import DomainError
from com.qode.qrew.v1.payments.core.observability import traced
from com.qode.qrew.v1.payments.core.payments import StripeClient
from com.qode.qrew.v1.payments.models.payment import Payment, PaymentStatus
from com.qode.qrew.v1.payments.repositories.payment import PaymentRepository
from com.qode.qrew.v1.payments.settings import settings

logger = structlog.get_logger(__name__)


class PaymentError(DomainError):
    pass


class PaymentExpiredError(DomainError):
    pass


@dataclass(frozen=True)
class _ReservationContext:
    amount_cents: int
    currency: str
    is_valid: bool
    error_code: str | None = None


async def _get_reservation_context(
    reservation_id: uuid.UUID, user_id: uuid.UUID
) -> _ReservationContext:
    async with httpx.AsyncClient(base_url=settings.monolith_url) as client:
        resp = await client.post(
            f"/internal/reservations/{reservation_id}/payment-context",
            json={"user_id": str(user_id)},
            headers={"X-Internal-Key": settings.internal_api_key},
            timeout=5.0,
        )
    if resp.status_code == 200:
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


async def _publish_event(subject: str, data: dict[str, Any], *, actor_id: uuid.UUID | None = None) -> None:
    try:
        from common.broker.publisher import publish as nats_publish
        from common.events.envelope import EventEnvelope

        event = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="payment",
            aggregate_id=data.get("payment_id", ""),
            actor_id=str(actor_id) if actor_id else None,
            data=data,
        )
        await nats_publish(subject, event)
    except Exception:
        await logger.awarning("nats_publish_failed", subject=subject)


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        repo: PaymentRepository,
        stripe: StripeClient,
    ) -> None:
        self._session = session
        self._repo = repo
        self._stripe = stripe

    @traced("payment.initiate")
    async def initiate(self, *, actor_id: uuid.UUID, reservation_id: uuid.UUID) -> Payment:
        ctx = await _get_reservation_context(reservation_id, actor_id)
        if not ctx.is_valid:
            if ctx.error_code in ("410", "expired"):
                raise PaymentExpiredError("Reservation has expired", field="expires_at")
            if ctx.error_code in ("404", "not_found", "wrong_owner"):
                raise PaymentError("Reservation not found", field="reservation_id")
            raise PaymentError("Reservation is not pending payment", field="status")

        existing = await self._repo.get_by_reservation_id(reservation_id)
        if existing is not None and existing.provider_payment_intent_id:
            return existing

        intent = await self._stripe.create_payment_intent(
            amount_cents=ctx.amount_cents,
            currency=ctx.currency,
            idempotency_key=f"reservation:{reservation_id}",
            metadata={"reservation_id": str(reservation_id)},
        )
        payment = existing or Payment(
            reservation_id=reservation_id,
            amount_cents=ctx.amount_cents,
            currency=ctx.currency,
        )
        payment.provider_payment_intent_id = intent.intent_id
        payment.client_secret_ciphertext = pii_crypto.encrypt(intent.client_secret)
        payment.status = _map_intent_status(intent.status)
        if existing is None:
            payment = await self._repo.insert(payment)
        else:
            await self._repo.flush()

        await _publish_event(
            "payments.payment.initiated.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(reservation_id),
                "amount_cents": ctx.amount_cents,
                "currency": ctx.currency,
            },
            actor_id=actor_id,
        )
        return payment

    def decrypt_client_secret(self, payment: Payment) -> str | None:
        if payment.client_secret_ciphertext is None:
            return None
        return pii_crypto.decrypt(payment.client_secret_ciphertext)

    @traced("payment.apply_succeeded")
    async def apply_succeeded(self, *, intent_id: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            await logger.awarning("payment_intent_unknown", intent_id=intent_id)
            return
        payment.status = PaymentStatus.succeeded
        await self._repo.flush()
        await _publish_event(
            "payments.payment.succeeded.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(payment.reservation_id),
            },
        )

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
            "payments.payment.failed.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(payment.reservation_id),
                "failure_code": failure_code,
                "failure_message": failure_message,
            },
        )

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
            "payments.payment.refunded.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(payment.reservation_id),
                "amount_refunded_cents": amount_refunded,
                "amount_total_cents": amount_total,
                "is_full_refund": is_full_refund,
            },
        )

    @traced("payment.apply_chargeback")
    async def apply_chargeback(self, *, intent_id: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        payment.status = PaymentStatus.refunded
        await self._repo.flush()
        await _publish_event(
            "payments.chargeback.opened.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(payment.reservation_id),
            },
        )

    @traced("payment.record_chargeback_closed")
    async def record_chargeback_closed(self, *, intent_id: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        await _publish_event(
            "payments.chargeback.closed.v1",
            {
                "payment_id": str(payment.id),
                "reservation_id": str(payment.reservation_id),
            },
        )

    async def update_intermediate(self, *, intent_id: str, status: str) -> None:
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        new_status = _map_intent_status(status)
        if new_status in {PaymentStatus.succeeded, PaymentStatus.failed}:
            return
        payment.status = new_status
        await self._repo.flush()


def _map_intent_status(stripe_status: str) -> PaymentStatus:
    mapping = {
        "succeeded": PaymentStatus.succeeded,
        "processing": PaymentStatus.processing,
        "requires_payment_method": PaymentStatus.requires_action,
        "requires_confirmation": PaymentStatus.requires_action,
        "requires_action": PaymentStatus.requires_action,
        "canceled": PaymentStatus.failed,
    }
    return mapping.get(stripe_status, PaymentStatus.requires_action)
