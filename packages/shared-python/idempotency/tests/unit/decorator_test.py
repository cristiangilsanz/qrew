# tests decorator
import asyncio

from idempotency.decorator import get_config, idempotent


class TestIdempotentDecorator:
    # verifies that attaches config to function
    def test_attaches_config_to_function(self) -> None:
        # handles handler
        @idempotent(scope="user", ttl_seconds=3600, required=True)
        async def handler() -> None:
            pass

        config = get_config(handler)
        assert config is not None
        assert config.scope == "user"
        assert config.ttl_seconds == 3600
        assert config.required is True

    # verifies that default values
    def test_default_values(self) -> None:
        # handles handler
        @idempotent()
        async def handler() -> None:
            pass

        config = get_config(handler)
        assert config is not None
        assert config.scope == "user"
        assert config.ttl_seconds == 86_400
        assert config.required is False

    # verifies that get config returns none for plain function
    def test_get_config_returns_none_for_plain_function(self) -> None:
        # handles plain
        async def plain() -> None:
            pass

        assert get_config(plain) is None

    # verifies that get config returns none for none
    def test_get_config_returns_none_for_none(self) -> None:
        assert get_config(None) is None

    # verifies that function still callable
    def test_function_still_callable(self) -> None:
        called = False

        # handles handler
        @idempotent()
        async def handler() -> None:
            nonlocal called
            called = True

        asyncio.get_event_loop().run_until_complete(handler())
        assert called
