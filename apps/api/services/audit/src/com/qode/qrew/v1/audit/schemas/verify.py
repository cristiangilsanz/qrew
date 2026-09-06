# defines the response schema for the chain verification endpoint
from pydantic import BaseModel


class AuditVerifyResponse(BaseModel):
    valid: bool
    event_count: int
    tampered_ids: list[str]
