import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PurchaseContext:
    """Inputs every fraud signal reads from. Stateless."""

    user_id: uuid.UUID
    user_created_at: datetime
    phone_number: str | None
    ip_address: str | None
    device_fingerprint_hash: str | None
    now: datetime
