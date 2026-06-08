import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from com.qode.qrew.v1.service.models.reservation import ReservationStatus
from com.qode.qrew.v1.service.models.ticket import TicketState


class ReservationCreateRequest(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int = Field(..., ge=1, le=20)


class ReservationTicketItem(BaseModel):
    id: uuid.UUID
    state: TicketState


class ReservationResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID
    quantity: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime
    tickets: list[ReservationTicketItem]
