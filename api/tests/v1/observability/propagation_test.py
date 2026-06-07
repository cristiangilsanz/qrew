from collections.abc import Generator
from typing import Any

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from com.qode.qrew.v1.service.core.observability import (
    CARRIER_KEY,
    extract_context,
    inject_current_context,
    setup_tracing,
    take_carrier,
    tracer,
)


@pytest.fixture
def memory_exporter() -> Generator[InMemorySpanExporter, None, None]:
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    setup_tracing(extra_processors=[processor])
    yield exporter
    processor.shutdown()
    exporter.clear()


def test_inject_returns_empty_when_no_active_span() -> None:
    assert inject_current_context() == {}


def test_inject_returns_carrier_inside_active_span(
    memory_exporter: InMemorySpanExporter,
) -> None:
    del memory_exporter
    with tracer.start_as_current_span("producer"):
        carrier = inject_current_context()
    assert "traceparent" in carrier


def test_extract_returns_none_for_empty_carrier() -> None:
    assert extract_context({}) is None
    assert extract_context(None) is None


def test_take_carrier_removes_reserved_key_only() -> None:
    payload: dict[str, Any] = {
        "user_id": "u-1",
        CARRIER_KEY: {"traceparent": "00-abc-def-01"},
    }
    carrier = take_carrier(payload)
    assert carrier == {"traceparent": "00-abc-def-01"}
    assert CARRIER_KEY not in payload
    assert payload == {"user_id": "u-1"}


def test_take_carrier_returns_none_for_payload_without_carrier() -> None:
    payload: dict[str, Any] = {"user_id": "u-1"}
    assert take_carrier(payload) is None
    assert payload == {"user_id": "u-1"}


def test_inject_then_extract_links_consumer_span_to_producer(
    memory_exporter: InMemorySpanExporter,
) -> None:
    with tracer.start_as_current_span("producer") as producer:
        producer_trace_id = producer.get_span_context().trace_id
        carrier = inject_current_context()

    parent = extract_context(carrier)
    with tracer.start_as_current_span("consumer", context=parent) as consumer:
        consumer_trace_id = consumer.get_span_context().trace_id

    finished = memory_exporter.get_finished_spans()
    names = {s.name for s in finished}
    assert {"producer", "consumer"} <= names
    assert producer_trace_id == consumer_trace_id
