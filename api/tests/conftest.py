import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from com.qode.qrew.v1.service.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
