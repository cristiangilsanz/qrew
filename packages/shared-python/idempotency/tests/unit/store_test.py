# tests store
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
    # verifies that user scope with id
    def test_user_scope_with_id(self) -> None:
        assert _scope_prefix("user", "abc") == "u:abc"

    # verifies that user scope anonymous
    def test_user_scope_anonymous(self) -> None:
        assert _scope_prefix("user", None) == "u:anon"

    # verifies that global scope
    def test_global_scope(self) -> None:
        assert _scope_prefix("global", None) == "g"
        assert _scope_prefix("global", "x") == "g"


class TestKeyBuilders:
    # verifies that result key user
    def test_result_key_user(self) -> None:
        key = _result_key("user", "u1", "k1")
        assert "u:u1" in key
        assert "k1" in key

    # verifies that lock key user
    def test_lock_key_user(self) -> None:
        key = _lock_key("user", "u1", "k1")
        assert "u:u1" in key
        assert "k1" in key

    # verifies that result and lock keys differ
    def test_result_and_lock_keys_differ(self) -> None:
        r = _result_key("global", None, "k")
        lk = _lock_key("global", None, "k")
        assert r != lk


class TestSerialisation:
    # verifies that round trip
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

    # verifies that binary body survives
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
    # verifies that removes set cookie
    def test_removes_set_cookie(self) -> None:
        result = sanitise_response_headers({"set-cookie": "s=1", "x-ok": "yes"})
        assert "set-cookie" not in result
        assert result["x-ok"] == "yes"

    # verifies that removes authorization
    def test_removes_authorization(self) -> None:
        result = sanitise_response_headers({"authorization": "Bearer t", "a": "b"})
        assert "authorization" not in result

    # verifies that extra blacklist
    def test_extra_blacklist(self) -> None:
        result = sanitise_response_headers(
            {"x-secret": "s", "ok": "yes"},
            extra_blacklist=frozenset({"x-secret"}),
        )
        assert "x-secret" not in result
        assert result["ok"] == "yes"


class TestIdempotencyStore:
    # handles make store
    def _make_store(self) -> tuple[IdempotencyStore, MagicMock]:
        redis = MagicMock()
        redis.set = AsyncMock(return_value=True)
        redis.get = AsyncMock(return_value=None)
        redis.delete = AsyncMock()
        store = IdempotencyStore(redis, lock_seconds=60)
        return store, redis

    # verifies that acquire lock succeeds
    async def test_acquire_lock_succeeds(self) -> None:
        store, _ = self._make_store()
        result = await store.acquire("global", None, "k1")
        assert result.acquired is True
        assert result.cached is None

    # verifies that acquire returns cached when lock fails
    async def test_acquire_returns_cached_when_lock_fails(self) -> None:
        store, redis = self._make_store()
        redis.set = AsyncMock(return_value=None)
        result = await store.acquire("global", None, "k1")
        assert result.acquired is False

    # verifies that fetch returns none when missing
    async def test_fetch_returns_none_when_missing(self) -> None:
        store, _ = self._make_store()
        result = await store.fetch("global", None, "k1")
        assert result is None

    # verifies that fetch deserialises stored response
    async def test_fetch_deserialises_stored_response(self) -> None:
        store, redis = self._make_store()
        resp = StoredResponse(200, {"x": "y"}, b"body", "fp")
        redis.get = AsyncMock(return_value=_serialise(resp).encode())
        result = await store.fetch("global", None, "k1")
        assert result is not None
        assert result.status_code == 200

    # verifies that save sets result and releases lock
    async def test_save_sets_result_and_releases_lock(self) -> None:
        store, redis = self._make_store()
        resp = StoredResponse(200, {}, b"", "fp")
        await store.save("global", None, "k1", resp, ttl_seconds=300)
        redis.set.assert_awaited()
        redis.delete.assert_awaited()

    # verifies that release lock failure is swallowed
    async def test_release_lock_failure_is_swallowed(self) -> None:
        store, redis = self._make_store()
        from redis.asyncio import RedisError

        redis.delete = AsyncMock(side_effect=RedisError("down"))
        await store.release("global", None, "k1")
