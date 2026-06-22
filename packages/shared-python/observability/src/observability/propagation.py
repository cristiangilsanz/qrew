from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace

CARRIER_KEY = "_otel"


def inject_current_context() -> dict[str, str]:
    """Captures the active trace context into a carrier when a valid span is present."""
    span = trace.get_current_span()
    if not span.get_span_context().is_valid:
        return {}
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


def extract_context(carrier: dict[str, str] | None) -> otel_context.Context | None:
    """Restores a trace context from an incoming propagation carrier."""
    if not carrier:
        return None
    return propagate.extract(carrier)


def take_carrier(payload: dict[str, Any] | None) -> dict[str, str] | None:
    """Removes and returns trace propagation data embedded in a message payload."""
    if not payload:
        return None
    raw = payload.pop(CARRIER_KEY, None)
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}  # type: ignore[misc]
    return None
