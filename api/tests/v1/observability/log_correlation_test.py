from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from com.qode.qrew.v1.service.core.observability.log_correlation import (
    add_trace_context,
)


def test_no_span_active_leaves_event_dict_unchanged() -> None:
    event_dict: dict[str, object] = {"event": "hello"}
    out = add_trace_context(None, "info", event_dict)
    assert "trace_id" not in out
    assert "span_id" not in out


def test_active_span_injects_trace_and_span_ids() -> None:
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("op"):
        out = add_trace_context(None, "info", {"event": "hello"})
    assert "trace_id" in out
    assert "span_id" in out
    assert len(out["trace_id"]) == 32  # type: ignore[arg-type]
    assert len(out["span_id"]) == 16  # type: ignore[arg-type]
