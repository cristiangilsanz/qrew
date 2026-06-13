from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-gate"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8001
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"

    # Shared internal secret for monolith → gate calls
    internal_api_key: str = "dev-internal-secret"
    # URL of the monolith API
    monolith_url: str = "http://localhost:8000"

    # Access JWT keys (same key material as monolith)
    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""

    # Ticket QR JWT keys (for verifying ticket JWTs at the gate)
    ticket_qr_jwt_private_key: str = ""
    ticket_qr_jwt_previous_public_keys: str = ""

    # Scanner JWT keys
    scanner_jwt_private_key: str = ""
    scanner_jwt_public_key: str = ""
    scanner_token_expire_hours: int = 12

    ticket_qr_audience: str = "qrew.scan"
    entry_replay_grace_seconds: int = 10
    entry_stats_cache_ttl_seconds: int = 5
    entry_stats_default_window_hours: int = 24

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_environment: str = "dev"

    ratelimit_enabled: bool = True
    ratelimit_fail_open: bool = True

    ws_enabled: bool = True
    ws_heartbeat_seconds: int = 30
    ws_pong_timeout_seconds: int = 10

    locking_default_ttl_seconds: float = 10.0
    locking_default_retry_attempts: int = 3
    locking_default_retry_delay_ms: int = 200


settings = Settings()
