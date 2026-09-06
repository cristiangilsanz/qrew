# defines the request and response schemas for the market
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from security import DocumentType, validate_document


class MarketQueueStatusResponse(BaseModel):
    in_queue: bool
    joined_at: datetime | None = None
    pending_assignment_id: uuid.UUID | None = None
    queue_count: int = 0


class MarketQueueJoinResponse(BaseModel):
    in_queue: bool
    joined_at: datetime


class MarketListingResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID
    price_cents: int
    currency: str
    state: str
    listed_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class MarketAssignmentResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    event_id: uuid.UUID
    ticket_type_id: uuid.UUID | None = None
    price_cents: int
    currency: str
    state: str
    assigned_at: datetime
    expires_at: datetime
    holder_name: str | None = None
    holder_document_type: DocumentType | None = None
    holder_dni: str | None = None
    event_name: str | None = None
    ticket_type_name: str | None = None


class MarketQueueEntryResponse(BaseModel):
    event_id: uuid.UUID
    joined_at: datetime


class MarketSetHoldersRequest(BaseModel):
    holder_name: str = Field(..., min_length=1, max_length=255)
    holder_document_type: DocumentType = DocumentType.dni
    holder_dni: str = Field(..., min_length=1, max_length=50)

    # validates a holder's document against the rules of the type it claims to be
    @model_validator(mode="after")
    def validate_holder_document(self) -> "MarketSetHoldersRequest":
        object.__setattr__(
            self, "holder_dni", validate_document(self.holder_dni, self.holder_document_type)
        )
        return self


class MarketAssignmentChargeResponse(BaseModel):
    amount_cents: int
    currency: str
