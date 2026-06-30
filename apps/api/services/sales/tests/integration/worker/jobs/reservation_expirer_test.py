import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.integration
async def test_sweep_expired_marks_reservation_expired(
    test_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import com.qode.qrew.v1.sales.worker.jobs.reservation_expirer as expirer

    monkeypatch.setattr(expirer, "AsyncSessionLocal", test_session_factory)

    event_id = uuid.uuid4()
    ticket_type_id = uuid.uuid4()
    reservation_id = uuid.uuid4()
    now = datetime.now(UTC)

    async with test_session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO sales.event_context
                (event_id, status, sale_starts_at, sale_ends_at, max_tickets_per_user,
                 queue_required, queue_admit_rate_per_minute)
                VALUES (:event_id, 'published', :sale_starts, :sale_ends, 10, false, 50)
            """),
            {
                "event_id": event_id,
                "sale_starts": now - timedelta(hours=2),
                "sale_ends": now + timedelta(hours=1),
            },
        )
        await session.execute(
            text("""
                INSERT INTO sales.ticket_type_inventory
                (ticket_type_id, event_id, capacity, reserved_count, price_cents, currency)
                VALUES (:ticket_type_id, :event_id, 100, 2, 1000, 'EUR')
            """),
            {"ticket_type_id": ticket_type_id, "event_id": event_id},
        )
        await session.execute(
            text("""
                INSERT INTO sales.reservations
                (id, user_id, event_id, ticket_type_id, quantity, status, expires_at)
                VALUES (:id, :user_id, :event_id, :ticket_type_id, 2, 'reserved', :expires_at)
            """),
            {
                "id": reservation_id,
                "user_id": uuid.uuid4(),
                "event_id": event_id,
                "ticket_type_id": ticket_type_id,
                "expires_at": now - timedelta(minutes=5),
            },
        )

    swept = await expirer.sweep_expired()
    assert swept >= 1

    async with test_session_factory() as session:
        row = await session.execute(
            text("SELECT status FROM sales.reservations WHERE id = :id"),
            {"id": reservation_id},
        )
        status = row.scalar_one()
    assert status == "expired"


@pytest.mark.integration
async def test_sweep_expired_decrements_inventory(
    test_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import com.qode.qrew.v1.sales.worker.jobs.reservation_expirer as expirer

    monkeypatch.setattr(expirer, "AsyncSessionLocal", test_session_factory)

    event_id = uuid.uuid4()
    ticket_type_id = uuid.uuid4()
    reservation_id = uuid.uuid4()
    now = datetime.now(UTC)

    async with test_session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO sales.event_context
                (event_id, status, sale_starts_at, sale_ends_at, max_tickets_per_user,
                 queue_required, queue_admit_rate_per_minute)
                VALUES (:event_id, 'published', :sale_starts, :sale_ends, 10, false, 50)
            """),
            {
                "event_id": event_id,
                "sale_starts": now - timedelta(hours=2),
                "sale_ends": now + timedelta(hours=1),
            },
        )
        await session.execute(
            text("""
                INSERT INTO sales.ticket_type_inventory
                (ticket_type_id, event_id, capacity, reserved_count, price_cents, currency)
                VALUES (:ticket_type_id, :event_id, 100, 3, 1000, 'EUR')
            """),
            {"ticket_type_id": ticket_type_id, "event_id": event_id},
        )
        await session.execute(
            text("""
                INSERT INTO sales.reservations
                (id, user_id, event_id, ticket_type_id, quantity, status, expires_at)
                VALUES (:id, :user_id, :event_id, :ticket_type_id, 3, 'reserved', :expires_at)
            """),
            {
                "id": reservation_id,
                "user_id": uuid.uuid4(),
                "event_id": event_id,
                "ticket_type_id": ticket_type_id,
                "expires_at": now - timedelta(minutes=5),
            },
        )

    await expirer.sweep_expired()

    async with test_session_factory() as session:
        row = await session.execute(
            text(
                "SELECT reserved_count FROM sales.ticket_type_inventory WHERE ticket_type_id = :id"
            ),
            {"id": ticket_type_id},
        )
        count = row.scalar_one()
    assert count == 0
