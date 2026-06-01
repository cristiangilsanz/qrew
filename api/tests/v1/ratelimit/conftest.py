from collections.abc import Iterator

import pytest

from com.qode.qrew.v1.service.settings import settings


@pytest.fixture(autouse=True)
def _enable_ratelimit() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Force the rate limiter on for the dedicated ratelimit tests."""
    previous = settings.ratelimit_enabled
    settings.ratelimit_enabled = True
    yield
    settings.ratelimit_enabled = previous
