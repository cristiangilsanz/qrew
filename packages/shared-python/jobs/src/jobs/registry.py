from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

JobHandler = Callable[..., Awaitable[Any]]

_DEFAULT_DELAYS = [30, 120, 600]


@dataclass
class CronFields:
    minute: set[int] | int | str = "*"
    hour: set[int] | int | str = "*"
    day: set[int] | int | str = "*"
    month: set[int] | int | str = "*"
    weekday: set[int] | int | str = "*"


@dataclass
class JobSpec:
    name: str
    handler: JobHandler
    max_attempts: int = 3
    retry_delays: list[int] = field(default_factory=lambda: list(_DEFAULT_DELAYS))
    cron_fields: CronFields | None = None


_registry: dict[str, JobSpec] = {}


def register(spec: JobSpec) -> None:
    """Registers a job specification under its name."""
    _registry[spec.name] = spec


def get_spec(name: str) -> JobSpec:
    """Returns the registered specification for a job name."""
    try:
        return _registry[name]
    except KeyError:
        from .errors import JobNotFoundError

        raise JobNotFoundError(name) from None


def all_specs() -> list[JobSpec]:
    """Returns all registered job specifications."""
    return list(_registry.values())


def parse_crontab(expr: str) -> CronFields:
    """Parse a standard five-field cron expression into structured fields."""
    parts = expr.strip().split()
    if len(parts) != 5:  # noqa: PLR2004
        raise ValueError(f"expected 5 cron fields, got {len(parts)}: {expr!r}")

    def _parse_field(val: str) -> set[int] | int | str:
        if val == "*":
            return "*"
        if "," in val:
            return {int(v) for v in val.split(",")}
        if val.lstrip("-").isdigit():
            return int(val)
        return val

    minute, hour, day, month, weekday = (_parse_field(p) for p in parts)
    return CronFields(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        weekday=weekday,
    )


def job(
    name: str,
    *,
    max_attempts: int = 3,
    retry_delays: list[int] | None = None,
    cron: CronFields | None = None,
) -> Callable[[JobHandler], JobHandler]:
    """Decorator that registers an async function as a named job."""

    def decorator(func: JobHandler) -> JobHandler:
        register(
            JobSpec(
                name=name,
                handler=func,
                max_attempts=max_attempts,
                retry_delays=retry_delays or list(_DEFAULT_DELAYS),
                cron_fields=cron,
            )
        )
        return func

    return decorator
