import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus


class ReservationCreateRequest(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int = Field(..., ge=1, le=20)
    reservation_window_token: str | None = Field(default=None, min_length=1)


class ReservationResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID
    quantity: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime


class HolderInput(BaseModel):
    position: int = Field(..., ge=1)
    holder_name: str = Field(..., min_length=1, max_length=255)
    holder_dni: str = Field(..., min_length=1, max_length=50)


class SetHoldersRequest(BaseModel):
    holders: list[HolderInput]


class HolderResponse(BaseModel):
    position: int
    holder_name: str
    holder_dni: str
