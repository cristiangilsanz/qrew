from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from arq.worker import Retry

from jobs.dlq import push_to_dlq
from jobs.registry import JobSpec
from observability import extract_context, take_carrier, tracer

logger = structlog.get_logger(__name__)

JobRunner = Callable[..., Awaitable[Any]]


def _payload_from_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    if len(args) == 1 and isinstance(args[0], dict):
        return dict(args[0])  # type: ignore[arg-type]
    return {"args": list(args), "kwargs": kwargs}


def _take_propagation_context(
    args: tuple[Any, ...], kwargs: dict[str, Any]
) -> tuple[tuple[Any, ...], dict[str, str] | None]:
    """Extracts and removes the trace propagation carrier from incoming job arguments."""
    if not args:
        return args, take_carrier(kwargs)
    head = args[0]
    if isinstance(head, dict):
        carrier = take_carrier(head)  # type: ignore[arg-type]
        return args, carrier
    return args, take_carrier(kwargs)


def wrap_handler(spec: JobSpec) -> JobRunner:
    """Wraps a job handler with logging, tracing, retry logic, and dead-letter routing."""

    async def runner(ctx: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        attempt = int(ctx.get("job_try", 1))
        job_id = str(ctx.get("job_id", "unknown"))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            job_name=spec.name, job_id=job_id, attempt=attempt
        )
        args, carrier = _take_propagation_context(args, kwargs)
        parent_context = extract_context(carrier)
        try:
            with tracer.start_as_current_span(
                f"job.{spec.name}", context=parent_context
            ) as span:
                span.set_attribute("job.name", spec.name)
                span.set_attribute("job.id", job_id)
                span.set_attribute("job.attempt", attempt)
                await logger.ainfo("job_started")
                result = await spec.handler(ctx, *args, **kwargs)
                await logger.ainfo("job_completed")
                return result
        except Retry:
            raise
        except BaseException as exc:
            await logger.aexception("job_failed", error=repr(exc))
            if attempt >= spec.max_attempts:
                await push_to_dlq(
                    ctx["redis"],
                    job_name=spec.name,
                    job_id=job_id,
                    payload=_payload_from_args(args, kwargs),
                    error=exc,
                )
                await logger.aerror("job_dead_lettered")
                return None
            delay = spec.retry_delays[attempt - 1]
            raise Retry(defer=delay) from exc
        finally:
            structlog.contextvars.clear_contextvars()

    runner.__name__ = spec.name.replace(".", "_")
    return runner
