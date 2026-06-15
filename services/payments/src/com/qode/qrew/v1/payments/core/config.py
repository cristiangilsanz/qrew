from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-payments"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8002
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"

    internal_api_key: str = "dev-internal-secret"
    sales_url: str = "http://localhost:8005"

    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""

    pii_encryption_key: str = ""
    pii_encryption_previous_keys: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_signing_secret: str = ""
    stripe_api_version: str = "2024-06-20"
    payments_default_currency: str = "EUR"
    payments_webhook_idempotency_ttl_seconds: int = 86400

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_environment: str = "dev"

    ratelimit_enabled: bool = True
    ratelimit_fail_open: bool = True

    locking_default_ttl_seconds: float = 10.0
    locking_default_retry_attempts: int = 3
    locking_default_retry_delay_ms: int = 200


settings = Settings()
