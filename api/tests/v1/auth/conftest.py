import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from com.qode.qrew.v1.service.core.auth import get_current_user
from com.qode.qrew.v1.service.core.limiter import limiter
from com.qode.qrew.v1.service.core.security import create_access_token
from com.qode.qrew.v1.service.main import app
from com.qode.qrew.v1.service.models.user import User


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Clear slowapi's in-memory storage before each test."""
    limiter.reset()


@pytest_asyncio.fixture
async def authenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Test client with a valid full-access token and a stubbed current user."""
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id))

    fake_user = User(
        id=user_id,
        full_name="Test User",
        email="test@example.com",
        phone_number="+34600000001",
        hashed_password="x",
        is_active=True,
        is_admin=False,
        terms_accepted_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        registration_ip="127.0.0.1",
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_current_user, None)
