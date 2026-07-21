import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus

_DNI_RE = re.compile(r"^\d{8}[A-Z]$")
_NIE_RE = re.compile(r"^[XYZ]\d{7}[A-Z]$")
_LETTER_MAP = "TRWAGMYFPDXBNJZSQVHLCKE"
_NIE_PREFIX = {"X": "0", "Y": "1", "Z": "2"}


def _valid_dni_letter(digits: str, letter: str) -> bool:
    return _LETTER_MAP[int(digits) % 23] == letter


def validate_spanish_id(value: str) -> str:
    v = value.strip().upper()
    if _DNI_RE.match(v):
        if not _valid_dni_letter(v[:8], v[8]):
            raise ValueError("Invalid DNI check letter")
        return v
    if _NIE_RE.match(v):
        digits = _NIE_PREFIX[v[0]] + v[1:8]
        if not _valid_dni_letter(digits, v[8]):
            raise ValueError("Invalid NIE check letter")
        return v
    raise ValueError("Must be a valid Spanish DNI (8 digits + letter) or NIE (X/Y/Z + 7 digits + letter)")


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

    @field_validator("holder_dni")
    @classmethod
    def validate_dni(cls, v: str) -> str:
        return validate_spanish_id(v)


class SetHoldersRequest(BaseModel):
    holders: list[HolderInput]


class HolderResponse(BaseModel):
    position: int
    holder_name: str
    holder_dni: str
