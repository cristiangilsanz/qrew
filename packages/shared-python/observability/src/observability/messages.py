# runs a message handler inside the span the publisher left in the envelope
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, cast

from opentelemetry.trace import SpanKind

from .propagation import CARRIER_KEY, extract_context
from .tracing import tracer

Handler = Callable[[bytes], Awaitable[None]]


# reads the trace carrier an envelope carries, if it carries one
def carrier_of(raw: bytes) -> dict[str, str] | None:
    try:
        body: Any = json.loads(raw.decode())
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    envelope = cast("dict[str, Any]", body)
    found = envelope.get(CARRIER_KEY) or envelope.get("otel")
    if not isinstance(found, dict):
        return None
    pairs = cast("dict[str, Any]", found)
    return {str(k): str(v) for k, v in pairs.items() if v is not None}


# runs the handler under the trace that produced the event
async def consume_traced(handler: Handler, raw: bytes, *, subject: str) -> None:
    parent = extract_context(carrier_of(raw))
    with tracer.start_as_current_span(subject, context=parent, kind=SpanKind.CONSUMER):
        await handler(raw)


# wraps a broker callback so it runs inside the trace the envelope carries
def traced_message(
    subject: str | None = None,
) -> Callable[[Callable[[Any], Awaitable[None]]], Callable[[Any], Awaitable[None]]]:

    # wraps the callback with the span the publisher opened
    def decorator(
        func: Callable[[Any], Awaitable[None]],
    ) -> Callable[[Any], Awaitable[None]]:
        # runs the callback under the trace the message carries
        @wraps(func)
        async def wrapper(msg: Any) -> None:
            parent = extract_context(carrier_of(msg.data))
            name = subject or str(getattr(msg, "subject", "message"))
            with tracer.start_as_current_span(
                name, context=parent, kind=SpanKind.CONSUMER
            ):
                await func(msg)

        return wrapper

    return decorator
