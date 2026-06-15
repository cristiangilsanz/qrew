from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-ticketing"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8004
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"

    internal_api_key: str = "dev-internal-secret"

    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""
    ticket_qr_jwt_private_key: str = ""
    ticket_qr_jwt_previous_public_keys: str = ""

    ticket_qr_ttl_seconds: int = 20
    ticket_qr_reassert_window_seconds: int = 30
    ticket_qr_mint_audit_sample_rate: int = 10
    ticket_qr_attestation_max_age_hours: int = 24
    ticket_qr_audience: str = "qrew.scan"
    ticket_qr_stream_max_seconds: int = 1800

    payments_default_currency: str = "GBP"

    locking_default_ttl_seconds: float = 10.0
    locking_default_retry_attempts: int = 3
    locking_default_retry_delay_ms: int = 200

    idempotency_enabled: bool = True
    idempotency_default_ttl_seconds: int = 86_400
    idempotency_lock_seconds: int = 30

    ratelimit_enabled: bool = True

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4318"
    otel_environment: str = "development"


settings = Settings()
