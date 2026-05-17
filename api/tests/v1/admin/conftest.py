import pytest

from com.qode.qrew.v1.service.core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Clear slowapi's in-memory storage before each test."""
    limiter.reset()
