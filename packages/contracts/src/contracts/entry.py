from __future__ import annotations

import uuid

from pydantic import BaseModel


class EntryValidatedData(BaseModel):
    ticket_id: uuid.UUID
    event_id: uuid.UUID
    venue_id: uuid.UUID
    scanner_id: uuid.UUID


class EntryRejectedData(BaseModel):
    ticket_id: uuid.UUID | None
    event_id: uuid.UUID | None
    scanner_id: uuid.UUID
    reason: str
