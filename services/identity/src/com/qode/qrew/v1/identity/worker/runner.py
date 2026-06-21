import asyncio

from db.redis import redis_settings_from_url
from jobs import build_worker_settings
from com.qode.qrew.v1.identity.core.config import settings

import com.qode.qrew.v1.identity.worker.jobs.auth_cleaner  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.identity.worker.jobs.lifecycle_notifier  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.identity.worker.jobs.notification_deliverer  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.identity.worker.jobs.outbox_drainer  # noqa: F401  # pyright: ignore[reportUnusedImport]
import com.qode.qrew.v1.identity.worker.jobs.storage_retainer  # noqa: F401  # pyright: ignore[reportUnusedImport]

WorkerSettings = build_worker_settings(redis_settings_from_url(settings.redis_url))


def main() -> None:
    from arq import run_worker

    asyncio.run(run_worker(WorkerSettings))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
