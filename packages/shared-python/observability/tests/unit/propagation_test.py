from unittest.mock import MagicMock, patch

from observability.propagation import (
    extract_context,
    inject_current_context,
    take_carrier,
)


class TestTakeCarrier:
    def test_removes_and_returns_otel_key(self) -> None:
        payload = {"_otel": {"traceparent": "abc"}, "data": 1}
        result = take_carrier(payload)
        assert result == {"traceparent": "abc"}
        assert "_otel" not in payload

    def test_missing_key_returns_none(self) -> None:
        payload = {"data": 1}
        result = take_carrier(payload)
        assert result is None
        assert payload == {"data": 1}

    def test_none_payload_returns_none(self) -> None:
        assert take_carrier(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert take_carrier({}) is None


class TestExtractContext:
    def test_none_returns_none(self) -> None:
        assert extract_context(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert extract_context({}) is None

    def test_non_empty_carrier_calls_propagate_extract(self) -> None:
        sentinel = MagicMock()
        with patch(
            "opentelemetry.propagate.extract", return_value=sentinel
        ) as mock_extract:
            result = extract_context({"traceparent": "abc"})
        mock_extract.assert_called_once_with({"traceparent": "abc"})
        assert result is sentinel


class TestInjectCurrentContext:
    def test_invalid_span_returns_empty_dict(self) -> None:
        ctx = MagicMock()
        ctx.is_valid = False
        span = MagicMock()
        span.get_span_context.return_value = ctx
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            result = inject_current_context()
        assert result == {}

    def test_valid_span_injects_and_returns_carrier(self) -> None:
        ctx = MagicMock()
        ctx.is_valid = True
        span = MagicMock()
        span.get_span_context.return_value = ctx

        def _fake_inject(carrier: dict) -> None:
            carrier["traceparent"] = "00-abc-def-01"

        with (
            patch("opentelemetry.trace.get_current_span", return_value=span),
            patch("opentelemetry.propagate.inject", side_effect=_fake_inject),
        ):
            result = inject_current_context()
        assert result == {"traceparent": "00-abc-def-01"}
