# entry point that starts the ticketing arq worker
import asyncio

from db.redis import redis_settings_from_url
from jobs import build_worker_settings
from com.qode.qrew.v1.ticketing.core.config import settings

import com.qode.qrew.v1.ticketing.worker.jobs.expired_ticket_purger  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.ticketing.worker.jobs.scanning_reverter  # noqa: F401  # pyright: ignore[reportUnusedImport]

WorkerSettings = build_worker_settings(
    redis_settings_from_url(settings.redis_url), queue_name="qrew:jobs:ticketing"
)


# runs the arq worker loop
def main() -> None:
    from arq import run_worker

    asyncio.run(run_worker(WorkerSettings))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
