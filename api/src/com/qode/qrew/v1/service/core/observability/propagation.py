from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace

CARRIER_KEY = "_otel"


def inject_current_context() -> dict[str, str]:
    """Capture the current trace context into a carrier dict, when valid."""
    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return {}
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


def extract_context(carrier: dict[str, str] | None) -> otel_context.Context | None:
    """Build an OpenTelemetry context from a carrier dict, or return None."""
    if not carrier:
        return None
    return propagate.extract(carrier)


def take_carrier(payload: dict[str, Any] | None) -> dict[str, str] | None:
    """Pop the reserved carrier key from a payload, leaving the rest untouched."""
    if not payload:
        return None
    raw = payload.pop(CARRIER_KEY, None)
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}  # type: ignore[misc]
    return None
