import asyncio

import structlog
from arq.cron import CronJob, cron
from arq.worker import func

from infra.redis import redis_settings_from_url
from com.qode.qrew.v1.catalog.worker.jobs.search_reindex import reindex_event, reindex_events
from com.qode.qrew.v1.catalog.settings import settings

logger = structlog.get_logger(__name__)


class WorkerSettings:
    functions = [
        func(reindex_event, name="search.reindex_event", max_tries=3),
    ]
    cron_jobs: list[CronJob] = [
        cron(reindex_events, name="cron:search.reindex_events", hour={5}, minute={0}, max_tries=1),
    ]
    redis_settings = redis_settings_from_url(settings.redis_url)
    max_jobs = 5
    job_timeout = 300
    keep_result = 60


def main() -> None:
    from arq import run_worker

    asyncio.run(run_worker(WorkerSettings))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
