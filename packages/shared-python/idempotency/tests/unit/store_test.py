from unittest.mock import AsyncMock, MagicMock

from idempotency.store import (
    IdempotencyStore,
    StoredResponse,
    _deserialise,
    _lock_key,
    _result_key,
    _scope_prefix,
    _serialise,
    sanitise_response_headers,
)


class TestScopePrefix:
    def test_user_scope_with_id(self) -> None:
        assert _scope_prefix("user", "abc") == "u:abc"

    def test_user_scope_anonymous(self) -> None:
        assert _scope_prefix("user", None) == "u:anon"

    def test_global_scope(self) -> None:
        assert _scope_prefix("global", None) == "g"
        assert _scope_prefix("global", "x") == "g"


class TestKeyBuilders:
    def test_result_key_user(self) -> None:
        key = _result_key("user", "u1", "k1")
        assert "u:u1" in key
        assert "k1" in key

    def test_lock_key_user(self) -> None:
        key = _lock_key("user", "u1", "k1")
        assert "u:u1" in key
        assert "k1" in key

    def test_result_and_lock_keys_differ(self) -> None:
        r = _result_key("global", None, "k")
        lk = _lock_key("global", None, "k")
        assert r != lk


class TestSerialisation:
    def test_round_trip(self) -> None:
        original = StoredResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body=b'{"ok":true}',
            fingerprint="abc123",
        )
        raw = _serialise(original)
        restored = _deserialise(raw)
        assert restored.status_code == 200
        assert restored.body == b'{"ok":true}'
        assert restored.fingerprint == "abc123"
        assert restored.headers["content-type"] == "application/json"

    def test_binary_body_survives(self) -> None:
        original = StoredResponse(
            status_code=201,
            headers={},
            body=bytes(range(256)),
            fingerprint="x",
        )
        restored = _deserialise(_serialise(original))
        assert restored.body == bytes(range(256))


class TestSanitiseHeaders:
    def test_removes_set_cookie(self) -> None:
        result = sanitise_response_headers({"set-cookie": "s=1", "x-ok": "yes"})
        assert "set-cookie" not in result
        assert result["x-ok"] == "yes"

    def test_removes_authorization(self) -> None:
        result = sanitise_response_headers({"authorization": "Bearer t", "a": "b"})
        assert "authorization" not in result

    def test_extra_blacklist(self) -> None:
        result = sanitise_response_headers(
            {"x-secret": "s", "ok": "yes"},
            extra_blacklist=frozenset({"x-secret"}),
        )
        assert "x-secret" not in result
        assert result["ok"] == "yes"


class TestIdempotencyStore:
    def _make_store(self) -> tuple[IdempotencyStore, MagicMock]:
        redis = MagicMock()
        redis.set = AsyncMock(return_value=True)
        redis.get = AsyncMock(return_value=None)
        redis.delete = AsyncMock()
        store = IdempotencyStore(redis, lock_seconds=60)
        return store, redis

    async def test_acquire_lock_succeeds(self) -> None:
        store, redis = self._make_store()
        result = await store.acquire("global", None, "k1")
        assert result.acquired is True
        assert result.cached is None

    async def test_acquire_returns_cached_when_lock_fails(self) -> None:
        store, redis = self._make_store()
        redis.set = AsyncMock(return_value=None)
        result = await store.acquire("global", None, "k1")
        assert result.acquired is False

    async def test_fetch_returns_none_when_missing(self) -> None:
        store, redis = self._make_store()
        result = await store.fetch("global", None, "k1")
        assert result is None

    async def test_fetch_deserialises_stored_response(self) -> None:
        store, redis = self._make_store()
        resp = StoredResponse(200, {"x": "y"}, b"body", "fp")
        redis.get = AsyncMock(return_value=_serialise(resp).encode())
        result = await store.fetch("global", None, "k1")
        assert result is not None
        assert result.status_code == 200

    async def test_save_sets_result_and_releases_lock(self) -> None:
        store, redis = self._make_store()
        resp = StoredResponse(200, {}, b"", "fp")
        await store.save("global", None, "k1", resp, ttl_seconds=300)
        redis.set.assert_awaited()
        redis.delete.assert_awaited()

    async def test_release_lock_failure_is_swallowed(self) -> None:
        store, redis = self._make_store()
        from redis.asyncio import RedisError

        redis.delete = AsyncMock(side_effect=RedisError("down"))
        await store.release("global", None, "k1")
