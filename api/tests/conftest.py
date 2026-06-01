from collections.abc import AsyncGenerator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.settings import settings


@pytest.fixture(autouse=True)
def _disable_ratelimit() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Keep the new Redis-backed rate limiter off during route tests."""
    previous = settings.ratelimit_enabled
    settings.ratelimit_enabled = False
    yield
    settings.ratelimit_enabled = previous


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
