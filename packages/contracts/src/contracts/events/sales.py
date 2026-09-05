# defines the data schemas for sales' domain events, market subjects included
from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel


# carries one reserved tier and how many seats it holds
class ReservationItem(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int


# carries the attendee a paid seat is issued to
class ReservationHolder(BaseModel):
    position: int
    holder_name: str
    holder_document_type: str
    holder_dni: str


class ReservationCreatedData(BaseModel):
    SUBJECT: ClassVar[str] = "sales.reservation.created.v1"

    reservation_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    items: list[ReservationItem]
    quantity: int
    expires_at: datetime


class ReservationPaidData(BaseModel):
    SUBJECT: ClassVar[str] = "sales.reservation.paid.v1"

    reservation_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    items: list[ReservationItem]
    quantity: int
    holders: list[ReservationHolder]


class ReservationCancelledData(BaseModel):
    SUBJECT: ClassVar[str] = "sales.reservation.cancelled.v1"

    reservation_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    items: list[ReservationItem]
    quantity: int


class ReservationExpiredData(BaseModel):
    SUBJECT: ClassVar[str] = "sales.reservation.expired.v1"

    reservation_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    items: list[ReservationItem]
    quantity: int | None = None


class MarketTicketFreezeData(BaseModel):
    SUBJECT: ClassVar[str] = "market.ticket.freeze.v1"

    ticket_id: uuid.UUID
    actor_id: uuid.UUID


class MarketTransferData(BaseModel):
    SUBJECT: ClassVar[str] = "market.transfer.v1"

    ticket_id: uuid.UUID
    new_owner_user_id: uuid.UUID
    holder_name: str
    holder_document_type: str
    holder_dni: str


class MarketListingExpiredData(BaseModel):
    SUBJECT: ClassVar[str] = "market.listing.expired.v1"

    ticket_id: uuid.UUID
    seller_user_id: uuid.UUID


class MarketAssignmentCreatedData(BaseModel):
    SUBJECT: ClassVar[str] = "market.assignment.created.v1"

    assignment_id: uuid.UUID
    buyer_user_id: uuid.UUID
