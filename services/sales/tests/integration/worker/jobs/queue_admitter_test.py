import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.integration
async def test_admit_next_no_active_queues(
    test_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fakeredis.aioredis
    import com.qode.qrew.v1.sales.worker.jobs.queue_admitter as admitter
    from com.qode.qrew.v1.sales.services.application.queue import storage as queue_storage
    from locking import lock as lock_module

    monkeypatch.setattr(admitter, "AsyncSessionLocal", test_session_factory)
    # Isolate from queue entries left by earlier tests in the shared Redis
    monkeypatch.setattr(
        queue_storage._ClientState, "client", fakeredis.aioredis.FakeRedis(decode_responses=True)
    )
    monkeypatch.setattr(lock_module._ClientState, "client", None)
    monkeypatch.setattr(lock_module._ClientState, "url", None)

    admitted = await admitter.admit_next()
    assert admitted == 0


@pytest.mark.integration
async def test_admit_next_admits_users_from_queue(
    test_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    fake_redis_server: object,
) -> None:
    import fakeredis.aioredis

    import com.qode.qrew.v1.sales.worker.jobs.queue_admitter as admitter
    from com.qode.qrew.v1.sales.services.application.queue.storage import (
        _ClientState as QueueClientState,
        join_queue,
    )
    from locking import lock as lock_module

    monkeypatch.setattr(admitter, "AsyncSessionLocal", test_session_factory)

    fake_redis = fakeredis.aioredis.FakeRedis(server=fake_redis_server, decode_responses=True)  # type: ignore[arg-type]
    QueueClientState.client = fake_redis
    lock_module._ClientState.client = None
    lock_module._ClientState.url = None

    event_id = uuid.uuid4()
    ticket_type_id = uuid.uuid4()
    now = datetime.now(UTC)

    async with test_session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO sales.event_context
                (event_id, status, sale_starts_at, sale_ends_at, max_tickets_per_user,
                 queue_required, queue_admit_rate_per_minute)
                VALUES (:event_id, 'published', :sale_starts, :sale_ends, 10, true, 5)
            """),
            {
                "event_id": event_id,
                "sale_starts": now - timedelta(hours=1),
                "sale_ends": now + timedelta(hours=1),
            },
        )
        await session.execute(
            text("""
                INSERT INTO sales.ticket_type_inventory
                (ticket_type_id, event_id, capacity, reserved_count, price_cents, currency)
                VALUES (:ticket_type_id, :event_id, 100, 0, 1000, 'EUR')
            """),
            {"ticket_type_id": ticket_type_id, "event_id": event_id},
        )

    now_ms = int(now.timestamp() * 1000)
    for i in range(3):
        await join_queue(
            event_id=event_id,
            user_id=uuid.uuid4(),
            sale_start_ms=now_ms,
            now_ms=now_ms,
            tiebreak=i,
        )

    admitted = await admitter.admit_next()
    assert admitted >= 1
