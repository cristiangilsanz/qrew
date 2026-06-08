import uuid
from datetime import datetime

from pydantic import BaseModel

from com.qode.qrew.v1.service.models.payment import PaymentStatus


class PaymentInitiateResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    amount_cents: int
    currency: str
    status: PaymentStatus
    client_secret: str
    created_at: datetime
