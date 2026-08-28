# carries the current trace context across process boundaries such as jobs and messages
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace

CARRIER_KEY = "_otel"


# injects the current trace context into a carrier dict
def inject_current_context() -> dict[str, str]:
    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return {}
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


# extracts a trace context from a carrier dict
def extract_context(carrier: dict[str, str] | None) -> otel_context.Context | None:
    if not carrier:
        return None
    return propagate.extract(carrier)


# pops the trace carrier out of a payload if it carries one
def take_carrier(payload: dict[str, Any] | None) -> dict[str, str] | None:
    if not payload:
        return None
    raw = payload.pop(CARRIER_KEY, None)
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}  # type: ignore[misc]
    return None
