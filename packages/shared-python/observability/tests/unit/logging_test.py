from unittest.mock import MagicMock, patch

from observability.logging import add_trace_context


def _make_span(
    *, is_valid: bool, trace_id: int = 0x1234ABCD, span_id: int = 0x5678EF01
) -> MagicMock:
    ctx = MagicMock()
    ctx.is_valid = is_valid
    ctx.trace_id = trace_id
    ctx.span_id = span_id
    span = MagicMock()
    span.get_span_context.return_value = ctx
    return span


class TestAddTraceContext:
    def test_valid_span_adds_trace_and_span_ids(self) -> None:
        span = _make_span(is_valid=True, trace_id=0x1234ABCD, span_id=0x5678EF01)
        event_dict: dict = {"event": "test"}
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            result = add_trace_context(None, None, event_dict)
        assert "trace_id" in result
        assert "span_id" in result
        assert result["trace_id"] == f"{0x1234ABCD:032x}"
        assert result["span_id"] == f"{0x5678EF01:016x}"

    def test_invalid_span_leaves_event_dict_unchanged(self) -> None:
        span = _make_span(is_valid=False)
        event_dict: dict = {"event": "test"}
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            result = add_trace_context(None, None, event_dict)
        assert "trace_id" not in result
        assert "span_id" not in result

    def test_returns_event_dict(self) -> None:
        span = _make_span(is_valid=False)
        event_dict: dict = {"event": "test"}
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            result = add_trace_context(None, None, event_dict)
        assert result is event_dict

    def test_returns_event_dict_with_valid_span(self) -> None:
        span = _make_span(is_valid=True)
        event_dict: dict = {"event": "test"}
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            result = add_trace_context(None, None, event_dict)
        assert result is event_dict
