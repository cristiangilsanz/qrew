from collections.abc import Generator
from typing import Any

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from com.qode.qrew.v1.service.core.jobs.context import wrap_handler
from com.qode.qrew.v1.service.core.jobs.registry import JobSpec
from com.qode.qrew.v1.service.core.observability import (
    inject_current_context,
    setup_tracing,
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


async def _noop(_ctx: dict[str, Any], _payload: dict[str, Any]) -> None:
    return None


def _spec() -> JobSpec:
    return JobSpec(
        name="test.linked",
        handler=_noop,
        max_attempts=1,
        retry_delays=(1, 5, 25, 125, 625),
        cron_fields=None,
    )


async def test_worker_span_inherits_trace_from_carrier(
    memory_exporter: InMemorySpanExporter,
) -> None:
    runner = wrap_handler(_spec())
    with tracer.start_as_current_span("producer") as producer:
        producer_trace_id = producer.get_span_context().trace_id
        carrier = inject_current_context()
    payload: dict[str, Any] = {"foo": "bar", "_otel": carrier}
    await runner({"job_try": 1, "job_id": "j1", "redis": None}, payload)

    job_span = next(
        s for s in memory_exporter.get_finished_spans() if s.name == "job.test.linked"
    )
    span_context = job_span.context
    assert span_context is not None
    assert span_context.trace_id == producer_trace_id
    assert job_span.parent is not None


async def test_worker_payload_otel_key_is_stripped_before_handler(
    memory_exporter: InMemorySpanExporter,
) -> None:
    del memory_exporter
    seen_payload: dict[str, Any] = {}

    async def _capture(_ctx: dict[str, Any], payload: dict[str, Any]) -> None:
        seen_payload.update(payload)

    spec = JobSpec(
        name="test.strip",
        handler=_capture,
        max_attempts=1,
        retry_delays=(1, 5, 25, 125, 625),
        cron_fields=None,
    )
    runner = wrap_handler(spec)
    with tracer.start_as_current_span("producer"):
        carrier = inject_current_context()
    payload: dict[str, Any] = {"hello": "world", "_otel": carrier}
    await runner({"job_try": 1, "job_id": "j2", "redis": None}, payload)
    assert "_otel" not in seen_payload
    assert seen_payload["hello"] == "world"
