from typing import Any

from arq.connections import RedisSettings
from arq.cron import CronJob, cron
from arq.worker import func

from jobs.context import wrap_handler
from jobs.registry import JobSpec, all_specs


def _arq_function(spec: JobSpec, runner: Any) -> Any:
    return func(runner, name=spec.name, max_tries=spec.max_attempts + 1)


def _arq_field(val: set[int] | int | str) -> set[int] | int | None:
    return None if isinstance(val, str) else val


def _build_cron(spec: JobSpec, runner: Any) -> CronJob:
    f = spec.cron_fields
    assert f is not None
    return cron(
        runner,
        name=f"cron:{spec.name}",
        minute=_arq_field(f.minute),
        hour=_arq_field(f.hour),
        day=_arq_field(f.day),
        month=_arq_field(f.month),
        weekday=_arq_field(f.weekday),
        max_tries=spec.max_attempts + 1,
    )


def build_worker_settings(redis_settings: RedisSettings) -> type:
    """Assembles an Arq WorkerSettings class from all registered job specifications."""
    functions: list[Any] = []
    cron_jobs: list[CronJob] = []
    for spec in all_specs():
        runner = wrap_handler(spec)
        functions.append(_arq_function(spec, runner))
        if spec.cron_fields is not None:
            cron_jobs.append(_build_cron(spec, runner))

    class WorkerSettings:
        pass

    WorkerSettings.functions = functions  # type: ignore[attr-defined]
    WorkerSettings.cron_jobs = cron_jobs  # type: ignore[attr-defined]
    WorkerSettings.redis_settings = redis_settings  # type: ignore[attr-defined]
    WorkerSettings.max_jobs = 10  # type: ignore[attr-defined]
    WorkerSettings.job_timeout = 300  # type: ignore[attr-defined]
    WorkerSettings.keep_result = 60  # type: ignore[attr-defined]

    return WorkerSettings
