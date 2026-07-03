import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PurchaseContext:
    user_id: uuid.UUID
    ip_address: str | None
    device_fingerprint_hash: str | None
    now: datetime
