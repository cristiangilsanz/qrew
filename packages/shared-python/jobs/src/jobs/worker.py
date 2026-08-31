# builds an arq worker settings class from every registered job spec
from typing import Any

from arq.connections import RedisSettings
from arq.cron import CronJob, cron
from arq.worker import func

from .context import wrap_handler
from .registry import JobSpec, all_specs


# wraps a job spec into an arq function definition
def _arq_function(spec: JobSpec, runner: Any) -> Any:
    return func(runner, name=spec.name, max_tries=spec.max_attempts + 1)


# converts a cron field's wildcard marker into arq's expected form
def _arq_field(val: set[int] | int | str) -> set[int] | int | None:
    return None if isinstance(val, str) else val


# builds an arq cron job from a job spec's schedule
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


# builds the worker settings class arq runs from every registered job
def build_worker_settings(
    redis_settings: RedisSettings, *, queue_name: str | None = None
) -> type:
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
    if queue_name is not None:
        WorkerSettings.queue_name = queue_name  # type: ignore[attr-defined]

    return WorkerSettings
