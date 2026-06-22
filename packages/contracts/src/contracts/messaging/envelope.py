from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OtelCarrier(BaseModel):
    traceparent: str | None = None
    tracestate: str | None = None


class EventEnvelope(BaseModel):
    """Standard envelope carried by every domain event over the message broker."""

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    occurred_at: datetime
    aggregate_type: str
    aggregate_id: str
    actor_id: str | None = None
    data: dict[str, Any]
    otel: OtelCarrier = Field(default_factory=OtelCarrier, alias="_otel")

    model_config = {"populate_by_name": True}
