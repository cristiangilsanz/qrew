from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import AsyncClient

from com.qode.qrew.v1.service.core.infra.database import get_db
from com.qode.qrew.v1.service.main import app


@pytest_asyncio.fixture
async def fake_db_no_events() -> AsyncGenerator[None, None]:
    async def _db() -> AsyncGenerator[MagicMock, None]:
        session = MagicMock()

        async def _connection() -> MagicMock:
            connection = MagicMock()

            async def _run_sync(callable_: object) -> bool:
                del callable_
                return False

            connection.run_sync = _run_sync
            return connection

        session.connection = AsyncMock(side_effect=_connection)
        yield session

    app.dependency_overrides[get_db] = _db
    yield
    app.dependency_overrides.pop(get_db, None)


async def test_search_returns_empty_when_events_table_missing(
    client: AsyncClient, fake_db_no_events: None
) -> None:
    del fake_db_no_events
    response = await client.get("/v1/events/search?q=concert")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["next_cursor"] is None
