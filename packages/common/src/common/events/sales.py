from __future__ import annotations

import uuid

from pydantic import BaseModel


class ReservationCreatedData(BaseModel):
    reservation_id: uuid.UUID
    user_id: uuid.UUID
    ticket_type_id: uuid.UUID
    event_id: uuid.UUID
    quantity: int
    expires_at: str


class ReservationExpiredData(BaseModel):
    reservation_id: uuid.UUID


class ReservationCancelledData(BaseModel):
    reservation_id: uuid.UUID
    reason: str


class ReservationPaidData(BaseModel):
    reservation_id: uuid.UUID
    payment_id: uuid.UUID


class ReservationFlaggedData(BaseModel):
    reservation_id: uuid.UUID
    fraud_reason: str


class QueueJoinedData(BaseModel):
    queue_redemption_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    position: int


class QueueAdmittedData(BaseModel):
    queue_redemption_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
