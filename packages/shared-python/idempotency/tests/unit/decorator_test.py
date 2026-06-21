import asyncio

from idempotency.decorator import get_config, idempotent


class TestIdempotentDecorator:
    def test_attaches_config_to_function(self) -> None:
        @idempotent(scope="user", ttl_seconds=3600, required=True)
        async def handler() -> None:
            pass

        config = get_config(handler)
        assert config is not None
        assert config.scope == "user"
        assert config.ttl_seconds == 3600
        assert config.required is True

    def test_default_values(self) -> None:
        @idempotent()
        async def handler() -> None:
            pass

        config = get_config(handler)
        assert config is not None
        assert config.scope == "user"
        assert config.ttl_seconds == 86_400
        assert config.required is False

    def test_get_config_returns_none_for_plain_function(self) -> None:
        async def plain() -> None:
            pass

        assert get_config(plain) is None

    def test_get_config_returns_none_for_none(self) -> None:
        assert get_config(None) is None

    def test_function_still_callable(self) -> None:
        called = False

        @idempotent()
        async def handler() -> None:
            nonlocal called
            called = True

        asyncio.get_event_loop().run_until_complete(handler())
        assert called
