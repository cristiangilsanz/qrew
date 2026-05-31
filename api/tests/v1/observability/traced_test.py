from collections.abc import Generator

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from com.qode.qrew.v1.service.core.observability import setup_tracing, traced


@pytest.fixture
def memory_exporter() -> Generator[InMemorySpanExporter, None, None]:
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    setup_tracing(extra_processors=[processor])
    yield exporter
    processor.shutdown()
    exporter.clear()


async def test_traced_creates_span_with_expected_name(
    memory_exporter: InMemorySpanExporter,
) -> None:
    @traced("svc.do_work")
    async def do_work() -> int:
        return 42

    assert await do_work() == 42
    names = [s.name for s in memory_exporter.get_finished_spans()]
    assert "svc.do_work" in names


async def test_traced_records_exception_and_sets_error_status(
    memory_exporter: InMemorySpanExporter,
) -> None:
    @traced("svc.boom")
    async def boom() -> None:
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        await boom()

    span = next(s for s in memory_exporter.get_finished_spans() if s.name == "svc.boom")
    assert span.status.status_code == StatusCode.ERROR
    assert span.events
