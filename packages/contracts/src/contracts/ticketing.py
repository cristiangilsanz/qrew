from __future__ import annotations

import uuid

from pydantic import BaseModel


class TicketIssuedData(BaseModel):
    ticket_id: uuid.UUID
    reservation_id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID


class TicketFrozenData(BaseModel):
    ticket_id: uuid.UUID
    reason: str
    device_id: uuid.UUID | None = None


class TicketCancelledData(BaseModel):
    ticket_id: uuid.UUID
    reason: str


class TicketRestoredData(BaseModel):
    ticket_id: uuid.UUID
    user_id: uuid.UUID


class TicketUsedData(BaseModel):
    ticket_id: uuid.UUID
    event_id: uuid.UUID
    scanner_id: uuid.UUID


class QrMintedData(BaseModel):
    ticket_id: uuid.UUID
    jti: str


class QrDeniedData(BaseModel):
    ticket_id: uuid.UUID
    reason: str
