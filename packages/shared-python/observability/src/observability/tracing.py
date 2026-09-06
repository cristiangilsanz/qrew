# sets up opentelemetry tracing and instrumentation for a service
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


# builds the resource that identifies a service in its traces
def _build_resource(service_name: str, version: str, environment: str) -> Resource:
    return Resource.create(
        {
            "service.name": service_name,
            "service.version": version,
            "service.instance.id": socket.gethostname(),
            "deployment.environment": environment,
        }
    )


# configures the tracer provider and instruments the app database and http client
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
        instrument_app(app)


# instruments the web framework, which has to happen before the app serves a request
def instrument_app(app: FastAPI) -> None:
    if getattr(app, "_is_instrumented_by_opentelemetry", False):
        return
    FastAPIInstrumentor.instrument_app(app)


# shuts down the tracer provider
def shutdown_tracing() -> None:
    provider = _state.get("provider")
    if provider is not None:
        provider.shutdown()
    _state["initialised"] = False
    _state["provider"] = None


# wraps a function in a span that records any exception it raises
def traced(
    name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:

    # wraps the function with the tracing span
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        # runs the function inside a span recording any exception it raises
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
