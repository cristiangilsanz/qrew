import socket
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

_TRACER_NAME = "qrew"
tracer = trace.get_tracer(_TRACER_NAME)

_state: dict[str, Any] = {"initialised": False, "provider": None}

T = TypeVar("T")


def _build_resource(service_name: str, version: str, environment: str) -> Resource:
    return Resource.create(
        {
            "service.name": service_name,
            "service.version": version,
            "service.instance.id": socket.gethostname(),
            "deployment.environment": environment,
        }
    )


def setup_tracing(
    *,
    service_name: str,
    version: str,
    environment: str,
    otel_enabled: bool = False,
    otel_endpoint: str = "",
    engine: Any | None = None,
    app: FastAPI | None = None,
    extra_processors: list[SpanProcessor] | None = None,
) -> None:
    """Initialises the global tracer provider and auto-instrumentation for a service."""
    if not _state["initialised"]:
        provider = TracerProvider(
            resource=_build_resource(service_name, version, environment)
        )
        if otel_enabled and otel_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint))
            )
        trace.set_tracer_provider(provider)
        _state["provider"] = provider
        _state["initialised"] = True

        if engine is not None:
            SQLAlchemyInstrumentor().instrument(engine=engine)  # type: ignore[no-untyped-call]
        RedisInstrumentor().instrument()  # type: ignore[no-untyped-call]
        HTTPXClientInstrumentor().instrument()

    provider = _state["provider"]
    if extra_processors:
        for processor in extra_processors:
            provider.add_span_processor(processor)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)


def shutdown_tracing() -> None:
    """Flushes queued spans and shuts down the tracer provider."""
    provider = _state.get("provider")
    if provider is not None:
        provider.shutdown()
    _state["initialised"] = False
    _state["provider"] = None


def traced(
    name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Wraps an async function in a named tracing span, recording any raised exceptions."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            with tracer.start_as_current_span(name) as span:
                try:
                    return await func(*args, **kwargs)
                except BaseException as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, repr(exc)))
                    raise

        return wrapper

    return decorator
