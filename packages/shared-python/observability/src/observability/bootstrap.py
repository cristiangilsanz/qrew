# wires structured logging and tracing for a process that has no fastapi app
from typing import Any

import structlog

from .logging import add_trace_context
from .tracing import setup_tracing

_LOG_LEVEL_INFO = 20


# builds the structlog processor chain the services and the workers share
def _build_processors(*, debug: bool) -> list[Any]:
    renderer: Any = (
        structlog.dev.ConsoleRenderer()
        if debug
        else structlog.processors.JSONRenderer()
    )
    return [
        structlog.contextvars.merge_contextvars,
        add_trace_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        renderer,
    ]


# configures logging and tracing before a worker starts consuming anything
def setup_worker_observability(
    *,
    service_name: str,
    version: str,
    debug: bool,
    otel_enabled: bool = False,
    otel_endpoint: str = "",
    engine: Any | None = None,
) -> None:
    structlog.configure(
        processors=_build_processors(debug=debug),
        wrapper_class=structlog.make_filtering_bound_logger(_LOG_LEVEL_INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    setup_tracing(
        service_name=service_name,
        version=version,
        environment="development" if debug else "production",
        otel_enabled=otel_enabled,
        otel_endpoint=otel_endpoint,
        engine=engine,
    )
