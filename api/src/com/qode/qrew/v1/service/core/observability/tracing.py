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

from com.qode.qrew.v1.service.core.infra.database import engine
from com.qode.qrew.v1.service.settings import settings

_TRACER_NAME = "qrew-api"
tracer = trace.get_tracer(_TRACER_NAME)

_state: dict[str, Any] = {"initialised": False, "provider": None}

T = TypeVar("T")


def _build_resource() -> Resource:
    return Resource.create(
        {
            "service.name": settings.app_name,
            "service.version": settings.version,
            "service.instance.id": socket.gethostname(),
            "deployment.environment": settings.otel_environment,
        }
    )


def setup_tracing(
    app: FastAPI | None = None,
    *,
    extra_processors: list[SpanProcessor] | None = None,
) -> None:
    """Configure the global tracer provider and auto-instrumentation.

    Idempotent: subsequent calls are no-ops unless extra_processors are supplied.
    """
    if not _state["initialised"]:
        provider = TracerProvider(resource=_build_resource())
        if settings.otel_enabled:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint))
            )
        trace.set_tracer_provider(provider)
        _state["provider"] = provider
        _state["initialised"] = True

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)  # type: ignore[no-untyped-call]
        RedisInstrumentor().instrument()  # type: ignore[no-untyped-call]
        HTTPXClientInstrumentor().instrument()

    provider = _state["provider"]
    if extra_processors:
        for processor in extra_processors:
            provider.add_span_processor(processor)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)


def shutdown_tracing() -> None:
    """Flush queued spans on shutdown."""
    provider = _state.get("provider")
    if provider is not None:
        provider.shutdown()
    _state["initialised"] = False
    _state["provider"] = None


def traced(
    name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Wrap an async function in a span named `name`, recording exceptions."""

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
