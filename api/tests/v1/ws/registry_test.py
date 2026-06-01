from collections.abc import Iterator

import pytest

from com.qode.qrew.v1.service.core.ws import (
    channel,
    render_key,
    reset_for_tests,
    resolve,
)
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.auth.user import User


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    reset_for_tests()
    yield
    reset_for_tests()


async def _allow(user: User, params: dict[str, str], session: Session) -> bool:
    del user, params, session
    return True


def test_simple_pattern_matches() -> None:
    channel(key_pattern="me.{user_id}")(_allow)
    resolution = resolve("me.abc-123")
    assert resolution is not None
    _, params = resolution
    assert params == {"user_id": "abc-123"}


def test_pattern_does_not_cross_dots() -> None:
    channel(key_pattern="queue.event.{event_id}")(_allow)
    assert resolve("queue.event.42") is not None
    assert resolve("queue.event.42.extra") is None


def test_duplicate_pattern_rejected() -> None:
    channel(key_pattern="me.{user_id}")(_allow)
    with pytest.raises(ValueError, match="duplicate"):
        channel(key_pattern="me.{user_id}")(_allow)


def test_render_key_substitutes_placeholders() -> None:
    assert render_key("me.{user_id}", {"user_id": "u-1"}) == "me.u-1"
