import uuid
from datetime import datetime

from pydantic import BaseModel


class TicketResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID
    state: str
    state_updated_at: datetime | None
    issued_at: datetime | None
    expired_at: datetime | None
    holder_name: str | None
    holder_dni: str | None
    created_at: datetime
    qr_eligible: bool
    counts_toward_limit: bool
