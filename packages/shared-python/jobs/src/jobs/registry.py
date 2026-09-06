# registers a job's handler retry policy and cron schedule
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


# records a job spec under its name
def register(spec: JobSpec) -> None:
    _registry[spec.name] = spec


# looks up a registered job spec by name
def get_spec(name: str) -> JobSpec:
    try:
        return _registry[name]
    except KeyError:
        from .errors import JobNotFoundError

        raise JobNotFoundError(name) from None


# lists every registered job spec
def all_specs() -> list[JobSpec]:
    return list(_registry.values())


# parses a five field crontab expression into cron fields
def parse_crontab(expr: str) -> CronFields:
    parts = expr.strip().split()
    if len(parts) != 5:  # noqa: PLR2004
        raise ValueError(f"expected 5 cron fields, got {len(parts)}: {expr!r}")

    # parses one crontab field into a wildcard integer or set of integers
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


# registers a function as a job under the given name and retry policy
def job(
    name: str,
    *,
    max_attempts: int = 3,
    retry_delays: list[int] | None = None,
    cron: CronFields | None = None,
) -> Callable[[JobHandler], JobHandler]:

    # records the function as a job spec
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
