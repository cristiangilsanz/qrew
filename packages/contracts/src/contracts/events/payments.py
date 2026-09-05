# defines the data schemas for payments' domain events
from __future__ import annotations

import uuid
from typing import ClassVar

from pydantic import BaseModel


class PaymentInitiatedData(BaseModel):
    SUBJECT: ClassVar[str] = "payments.payment.initiated.v1"

    payment_id: uuid.UUID
    user_id: uuid.UUID
    amount_cents: int
    currency: str
    reservation_id: uuid.UUID | None = None
    market_assignment_id: uuid.UUID | None = None


class PaymentSucceededData(BaseModel):
    SUBJECT: ClassVar[str] = "payments.payment.succeeded.v1"

    payment_id: uuid.UUID
    user_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    market_assignment_id: uuid.UUID | None = None
    payment_intent_id: str | None = None


class PaymentFailedData(BaseModel):
    SUBJECT: ClassVar[str] = "payments.payment.failed.v1"

    payment_id: uuid.UUID
    user_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    market_assignment_id: uuid.UUID | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class PaymentRefundedData(BaseModel):
    SUBJECT: ClassVar[str] = "payments.payment.refunded.v1"

    payment_id: uuid.UUID
    user_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    market_assignment_id: uuid.UUID | None = None
    amount_refunded_cents: int
    amount_total_cents: int
    is_full_refund: bool


class ChargebackOpenedData(BaseModel):
    SUBJECT: ClassVar[str] = "payments.chargeback.opened.v1"

    payment_id: uuid.UUID
    user_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    market_assignment_id: uuid.UUID | None = None


class ChargebackClosedData(BaseModel):
    SUBJECT: ClassVar[str] = "payments.chargeback.closed.v1"

    payment_id: uuid.UUID
    user_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    market_assignment_id: uuid.UUID | None = None
