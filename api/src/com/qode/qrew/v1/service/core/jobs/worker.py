from typing import Any

from arq.cron import CronJob, cron
from arq.worker import func

import com.qode.qrew.v1.service.jobs as _job_handlers
from com.qode.qrew.v1.service.core.jobs.context import wrap_handler
from com.qode.qrew.v1.service.core.jobs.pool import redis_settings_from_url
from com.qode.qrew.v1.service.core.jobs.registry import JobSpec, all_specs

_ = _job_handlers  # ensure @job decorators register at import time


def _functions_and_crons() -> tuple[list[Any], list[CronJob]]:
    functions: list[Any] = []
    cron_jobs: list[CronJob] = []
    for spec in all_specs():
        runner = wrap_handler(spec)
        functions.append(_arq_function(spec, runner))
        if spec.cron_fields is not None:
            cron_jobs.append(_build_cron(spec, runner))
    return functions, cron_jobs


def _arq_function(spec: JobSpec, runner: Any) -> Any:
    return func(runner, name=spec.name, max_tries=spec.max_attempts + 1)


def _build_cron(spec: JobSpec, runner: Any) -> CronJob:
    f = spec.cron_fields
    assert f is not None
    return cron(
        runner,
        name=f"cron:{spec.name}",
        minute=f.minute,
        hour=f.hour,
        day=f.day,
        month=f.month,
        weekday=f.weekday,
        max_tries=spec.max_attempts + 1,
    )


_functions, _crons = _functions_and_crons()


class WorkerSettings:
    functions = _functions
    cron_jobs = _crons
    redis_settings = redis_settings_from_url()
    max_jobs = 10
    job_timeout = 300
    keep_result = 60
