from ratelimit.errors import RateLimitedError


class TestRateLimitedError:
    def test_str_includes_scope(self) -> None:
        err = RateLimitedError(scope="ip", limit=100, window_seconds=60, retry_after_seconds=5)
        assert "ip" in str(err)
        assert "100" in str(err)
        assert "60" in str(err)

    def test_is_exception(self) -> None:
        err = RateLimitedError(scope="user", limit=10, window_seconds=30, retry_after_seconds=2)
        assert isinstance(err, Exception)
