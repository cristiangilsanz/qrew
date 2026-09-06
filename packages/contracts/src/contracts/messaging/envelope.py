# defines the envelope every domain event is published inside
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from opentelemetry import propagate, trace
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class OtelCarrier(BaseModel):
    traceparent: str | None = None
    tracestate: str | None = None


# captures the trace context of whoever builds the envelope, so a consumer continues it
def _carrier_now() -> OtelCarrier:
    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return OtelCarrier()
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return OtelCarrier(**carrier)


class EventEnvelope(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    occurred_at: datetime
    aggregate_type: str
    aggregate_id: str
    actor_id: str | None = None
    data: dict[str, Any]
    otel: OtelCarrier = Field(
        default_factory=_carrier_now,
        validation_alias=AliasChoices("_otel", "otel"),
        serialization_alias="_otel",
    )

    model_config = ConfigDict(populate_by_name=True)
