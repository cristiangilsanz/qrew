from __future__ import annotations

import uuid

from pydantic import BaseModel


class PaymentInitiatedData(BaseModel):
    payment_id: uuid.UUID
    reservation_id: uuid.UUID
    amount_cents: int
    currency: str
    stripe_intent_id: str


class PaymentSucceededData(BaseModel):
    payment_id: uuid.UUID
    reservation_id: uuid.UUID
    amount_cents: int
    currency: str


class PaymentFailedData(BaseModel):
    payment_id: uuid.UUID
    reservation_id: uuid.UUID
    reason: str


class PaymentRefundedData(BaseModel):
    payment_id: uuid.UUID
    reservation_id: uuid.UUID
    refund_cents: int


class ChargebackOpenedData(BaseModel):
    payment_id: uuid.UUID
    reservation_id: uuid.UUID
    dispute_id: str
