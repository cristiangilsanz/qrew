from db.redis import redis_settings_from_url


class TestRedisSettingsFromUrl:
    def test_basic_url(self) -> None:
        s = redis_settings_from_url("redis://localhost:6379")
        assert s.host == "localhost"
        assert s.port == 6379
        assert s.database == 0
        assert s.ssl is False

    def test_database_from_path(self) -> None:
        s = redis_settings_from_url("redis://localhost:6379/2")
        assert s.database == 2

    def test_password_only(self) -> None:
        s = redis_settings_from_url("redis://:secret@host:6379")
        assert s.password == "secret"
        assert not s.username

    def test_username_and_password(self) -> None:
        s = redis_settings_from_url("redis://user:pass@host:6380/1")
        assert s.username == "user"
        assert s.password == "pass"
        assert s.port == 6380
        assert s.database == 1

    def test_rediss_scheme_sets_ssl(self) -> None:
        s = redis_settings_from_url("rediss://localhost:6380")
        assert s.ssl is True
