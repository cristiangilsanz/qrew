from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-sales"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8005
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"

    internal_api_key: str = "dev-internal-secret"
    payments_default_currency: str = "EUR"

    # Access JWT (shared with monolith/identity)
    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""

    # Queue JWT keys
    queue_jwt_private_key: str = ""
    queue_jwt_previous_public_keys: str = ""

    # Reservation settings
    reservation_ttl_seconds: int = 600
    reservation_sweep_batch_size: int = 100

    # Queue settings
    queue_join_lead_seconds: int = 300
    queue_redeem_window_seconds: int = 120
    queue_reservation_window_seconds: int = 300

    # Fraud settings
    fraud_signals_enabled: bool = True
    fraud_score_block_threshold: int = 80
    fraud_score_review_threshold: int = 40
    fraud_weight_account_age_recent: int = 50
    fraud_weight_account_age_young: int = 25
    fraud_weight_fingerprint_reuse: int = 40
    fraud_weight_voip_phone: int = 30
    fraud_weight_time_to_purchase_immediate: int = 50
    fraud_weight_time_to_purchase_fast: int = 30
    fraud_weight_ip_velocity: int = 35
    fraud_fingerprint_lookback_hours: int = 24
    fraud_fingerprint_threshold: int = 3
    fraud_ip_velocity_window_minutes: int = 10
    fraud_ip_velocity_threshold: int = 5
    fraud_time_to_purchase_threshold_minutes: int = 5

    # Observability
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_environment: str = "dev"

    # Rate limiting
    ratelimit_enabled: bool = True
    ratelimit_fail_open: bool = True

    # Idempotency
    idempotency_enabled: bool = True
    idempotency_default_ttl_seconds: int = 86_400
    idempotency_lock_seconds: int = 30

    # Locking
    locking_default_ttl_seconds: float = 10.0
    locking_default_retry_attempts: int = 3
    locking_default_retry_delay_ms: int = 200


settings = Settings()
