import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth import pii_crypto
from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.locking import redlock
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.core.outbox import publish_via_outbox
from com.qode.qrew.v1.service.core.payments import StripeClient
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.payment import Payment, PaymentStatus
from com.qode.qrew.v1.service.models.reservation import (
    Reservation,
    ReservationStatus,
)
from com.qode.qrew.v1.service.models.ticket import TicketState
from com.qode.qrew.v1.service.repositories.payment import PaymentRepository
from com.qode.qrew.v1.service.repositories.reservation import ReservationRepository
from com.qode.qrew.v1.service.repositories.ticket_type import TicketTypeRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket import transition_ticket
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class PaymentError(DomainError):
    """Raised when a payment operation fails a domain rule."""


class PaymentExpiredError(DomainError):
    """Raised when the reservation has already expired and cannot be paid."""


class PaymentService:
    """Business logic for the payment aggregate."""

    def __init__(
        self,
        session: AsyncSession,
        repo: PaymentRepository,
        reservation_repo: ReservationRepository,
        tier_repo: TicketTypeRepository,
        stripe: StripeClient,
        audit: AuditService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._reservation_repo = reservation_repo
        self._tier_repo = tier_repo
        self._stripe = stripe
        self._audit = audit

    @traced("payment.initiate")
    async def initiate(
        self,
        *,
        actor_id: uuid.UUID,
        reservation_id: uuid.UUID,
    ) -> Payment:
        """Create or return the PaymentIntent for a reservation."""
        from datetime import datetime, timezone

        reservation = await self._reservation_repo.get_by_id(reservation_id)
        if reservation is None or reservation.user_id != actor_id:
            raise PaymentError("Reservation not found", field="reservation_id")
        if reservation.status != ReservationStatus.reserved:
            raise PaymentError("Reservation is not pending payment", field="status")
        if reservation.expires_at <= datetime.now(timezone.utc):
            raise PaymentExpiredError("Reservation has expired", field="expires_at")
        existing = await self._repo.get_by_reservation_id(reservation.id)
        if existing is not None and existing.provider_payment_intent_id:
            return existing
        tier = await self._tier_repo.get_by_id(reservation.ticket_type_id)
        if tier is None:
            raise PaymentError("Ticket type not found", field="ticket_type_id")
        amount_cents = tier.price_cents * reservation.quantity
        currency = tier.currency or settings.payments_default_currency
        intent = await self._stripe.create_payment_intent(
            amount_cents=amount_cents,
            currency=currency,
            idempotency_key=f"reservation:{reservation.id}",
            metadata={"reservation_id": str(reservation.id)},
        )
        payment = existing or Payment(
            reservation_id=reservation.id,
            amount_cents=amount_cents,
            currency=currency,
        )
        payment.provider_payment_intent_id = intent.intent_id
        payment.client_secret_ciphertext = pii_crypto.encrypt(intent.client_secret)
        payment.status = _map_intent_status(intent.status)
        if existing is None:
            payment = await self._repo.insert(payment)
        else:
            await self._repo.flush()
        await self._record(
            AuditAction.PAYMENT_INITIATED,
            actor_id=actor_id,
            payment_id=payment.id,
            payload={
                "reservation_id": str(reservation.id),
                "amount_cents": amount_cents,
                "currency": currency,
            },
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
        reservation = await self._reservation_repo.get_by_id(payment.reservation_id)
        if reservation is None:
            return
        async with redlock(f"reservation:{reservation.id}:lifecycle", ttl_seconds=10):
            fresh = await self._reservation_repo.get_by_id(reservation.id)
            if fresh is None or fresh.status != ReservationStatus.reserved:
                payment.status = PaymentStatus.succeeded
                await self._repo.flush()
                return
            fresh.status = ReservationStatus.paid
            for ticket in await self._reservation_repo.list_tickets(fresh.id):
                if ticket.state == TicketState.reserved:
                    await transition_ticket(
                        self._session,
                        ticket_id=ticket.id,
                        to_state=TicketState.issued,
                        reason="payment_succeeded",
                        actor_id=fresh.user_id,
                        audit=self._audit,
                    )
            payment.status = PaymentStatus.succeeded
            await self._repo.flush()
            await publish_via_outbox(
                self._session,
                aggregate_type="payment",
                aggregate_id=str(payment.id),
                job_name="notifications.payment_succeeded",
                payload={"reservation_id": str(fresh.id)},
            )
            await self._record(
                AuditAction.PAYMENT_SUCCEEDED,
                actor_id=fresh.user_id,
                payment_id=payment.id,
                payload={"reservation_id": str(fresh.id)},
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
        await publish_via_outbox(
            self._session,
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            job_name="notifications.payment_failed",
            payload={
                "reservation_id": str(payment.reservation_id),
                "failure_code": failure_code,
            },
        )
        reservation = await self._reservation_repo.get_by_id(payment.reservation_id)
        await self._record(
            AuditAction.PAYMENT_FAILED,
            actor_id=reservation.user_id if reservation else uuid.uuid4(),
            payment_id=payment.id,
            payload={"failure_code": failure_code},
        )

    @traced("payment.apply_refund")
    async def apply_refund(
        self, *, intent_id: str, amount_refunded: int, amount_total: int
    ) -> None:
        """Handle charge.refunded; full refund cancels reservation and tickets."""
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        if amount_refunded < amount_total:
            await self._record(
                AuditAction.PAYMENT_PARTIAL_REFUND,
                actor_id=uuid.uuid4(),
                payment_id=payment.id,
                payload={
                    "amount_refunded": amount_refunded,
                    "amount_total": amount_total,
                },
            )
            return
        await self._cancel_for_payment(payment, reason=AuditAction.PAYMENT_REFUNDED)

    @traced("payment.apply_chargeback")
    async def apply_chargeback(self, *, intent_id: str) -> None:
        """Handle charge.dispute.created; cancel issued tickets immediately."""
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        await self._cancel_for_payment(payment, reason=AuditAction.CHARGEBACK_OPENED)

    @traced("payment.record_chargeback_closed")
    async def record_chargeback_closed(self, *, intent_id: str) -> None:
        """Log the dispute closing; the FSM has already moved."""
        payment = await self._repo.get_by_intent_id(intent_id)
        if payment is None:
            return
        reservation = await self._reservation_repo.get_by_id(payment.reservation_id)
        actor_id = reservation.user_id if reservation else uuid.uuid4()
        await self._record(
            AuditAction.CHARGEBACK_CLOSED,
            actor_id=actor_id,
            payment_id=payment.id,
            payload={},
        )

    async def _cancel_for_payment(
        self, payment: Payment, *, reason: AuditAction
    ) -> None:
        reservation = await self._reservation_repo.get_by_id(payment.reservation_id)
        if reservation is None:
            return
        async with redlock(f"reservation:{reservation.id}:lifecycle", ttl_seconds=10):
            tickets = await self._reservation_repo.list_tickets(reservation.id)
            used = [t for t in tickets if t.state == TicketState.used]
            if used:
                await self._record(
                    AuditAction.CHARGEBACK_ON_USED_TICKET,
                    actor_id=reservation.user_id,
                    payment_id=payment.id,
                    payload={
                        "used_ticket_ids": [str(t.id) for t in used],
                        "reason": reason.value,
                    },
                )
            cancellable_states = {TicketState.reserved, TicketState.issued}
            qty_to_release = 0
            for ticket in tickets:
                if ticket.state in cancellable_states:
                    await transition_ticket(
                        self._session,
                        ticket_id=ticket.id,
                        to_state=TicketState.cancelled,
                        reason=reason.value,
                        actor_id=reservation.user_id,
                        audit=self._audit,
                    )
                    qty_to_release += 1
            if qty_to_release > 0:
                tier = await self._tier_repo.get_by_id(reservation.ticket_type_id)
                if tier is not None:
                    tier.reserved_count = max(0, tier.reserved_count - qty_to_release)
            reservation.status = ReservationStatus.cancelled
            payment.status = PaymentStatus.refunded
            await self._repo.flush()
            job_name = (
                "notifications.ticket_cancelled_chargeback"
                if reason == AuditAction.CHARGEBACK_OPENED
                else "notifications.ticket_cancelled_refund"
            )
            await publish_via_outbox(
                self._session,
                aggregate_type="payment",
                aggregate_id=str(payment.id),
                job_name=job_name,
                payload={
                    "reservation_id": str(reservation.id),
                    "reason": reason.value,
                },
            )
            await self._record(
                reason,
                actor_id=reservation.user_id,
                payment_id=payment.id,
                payload={"reservation_id": str(reservation.id)},
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

    async def _record(
        self,
        action: AuditAction,
        *,
        actor_id: uuid.UUID,
        payment_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        try:
            await self._audit.record(
                action=action,
                actor_id=actor_id,
                entity_type="payment",
                entity_id=str(payment_id),
                payload=payload,
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=action)


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


_ = Reservation  # noqa: B018 keep import for type completeness
