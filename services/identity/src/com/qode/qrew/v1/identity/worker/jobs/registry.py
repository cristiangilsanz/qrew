from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from jobs.registry import CronFields, parse_crontab

JobHandler = Callable[..., Awaitable[Any]]

DEFAULT_RETRY_DELAYS_SECONDS: tuple[int, ...] = (1, 5, 25, 125, 625)


@dataclass
class JobSpec:
    name: str
    handler: JobHandler
    max_attempts: int
    retry_delays: tuple[int, ...]
    cron_fields: CronFields | None


_REGISTRY: dict[str, JobSpec] = {}


def job(
    *,
    name: str,
    cron: str | None = None,
    max_attempts: int = 5,
    retry_delays: tuple[int, ...] = DEFAULT_RETRY_DELAYS_SECONDS,
) -> Callable[[JobHandler], JobHandler]:
    """Register a coroutine as a background job."""

    def decorator(handler: JobHandler) -> JobHandler:
        if name in _REGISTRY:
            raise ValueError(f"duplicate job name: {name}")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if len(retry_delays) < max_attempts - 1:
            raise ValueError("retry_delays must cover max_attempts - 1 entries")
        _REGISTRY[name] = JobSpec(
            name=name,
            handler=handler,
            max_attempts=max_attempts,
            retry_delays=retry_delays,
            cron_fields=parse_crontab(cron) if cron else None,
        )
        return handler

    return decorator


def all_specs() -> list[JobSpec]:
    return list(_REGISTRY.values())


def get_spec(name: str) -> JobSpec:
    return _REGISTRY[name]


def reset_registry_for_tests() -> None:
    _REGISTRY.clear()
