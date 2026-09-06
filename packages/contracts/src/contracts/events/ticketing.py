# defines the data schemas for ticketing's domain events
from __future__ import annotations

import uuid
from typing import ClassVar

from pydantic import BaseModel


class TicketStateChangedData(BaseModel):
    SUBJECT: ClassVar[str] = "ticketing.ticket.state_changed.v1"

    ticket_id: uuid.UUID
    event_id: uuid.UUID
    state: str
    previous_state: str
    owner_user_id: uuid.UUID
    bound_device_id: uuid.UUID | None = None


class TicketRestoredData(BaseModel):
    SUBJECT: ClassVar[str] = "ticketing.ticket.restored.v1"

    ticket_id: uuid.UUID
    user_id: uuid.UUID
