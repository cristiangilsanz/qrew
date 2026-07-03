import asyncio

from db.redis import redis_settings_from_url
from jobs import build_worker_settings
from com.qode.qrew.v1.catalog.core.config import settings

import com.qode.qrew.v1.catalog.worker.jobs.search_reindexer  # noqa: F401  # pyright: ignore[reportUnusedImport]


WorkerSettings = build_worker_settings(redis_settings_from_url(settings.redis_url))


def main() -> None:
    from arq import run_worker

    asyncio.run(run_worker(WorkerSettings))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
