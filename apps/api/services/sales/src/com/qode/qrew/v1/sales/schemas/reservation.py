# defines the request and response schemas for reservations and their holders
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator
from security import DocumentType, validate_document

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus


class ReservationItemInput(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int = Field(..., ge=1, le=20)


class ReservationCreateRequest(BaseModel):
    items: list[ReservationItemInput] = Field(..., min_length=1, max_length=10)
    reservation_window_token: str | None = Field(default=None, min_length=1)


class ReservationItemResponse(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int


class ReservationResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    items: list[ReservationItemResponse]
    quantity: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime


class HolderInput(BaseModel):
    position: int = Field(..., ge=1)
    holder_name: str = Field(..., min_length=1, max_length=255)
    holder_document_type: DocumentType = DocumentType.dni
    holder_dni: str = Field(..., min_length=1, max_length=50)

    # validates a holder's document against the rules of the type it claims to be
    @model_validator(mode="after")
    def validate_holder_document(self) -> "HolderInput":
        object.__setattr__(
            self, "holder_dni", validate_document(self.holder_dni, self.holder_document_type)
        )
        return self


class SetHoldersRequest(BaseModel):
    holders: list[HolderInput]


class HolderResponse(BaseModel):
    position: int
    holder_name: str
    holder_document_type: DocumentType
    holder_dni: str
