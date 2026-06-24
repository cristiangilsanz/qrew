from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_SERVICE_DIR = Path(__file__).parents[7]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=str(_SERVICE_DIR / "config" / "local.yaml"),
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-sales"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8005
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = ""

    internal_api_key: str = ""
    payments_default_currency: str = "EUR"

    access_jwt_private_key: str = ""
    queue_jwt_private_key: str = ""

    reservation_ttl_seconds: int = 600
    reservation_sweep_batch_size: int = 100

    queue_join_lead_seconds: int = 300
    queue_redeem_window_seconds: int = 120
    queue_reservation_window_seconds: int = 300

    fraud_signals_enabled: bool = True
    fraud_score_block_threshold: int = 80
    fraud_score_review_threshold: int = 40
    fraud_weight_account_age_recent: int = 50
    fraud_weight_account_age_young: int = 25
    fraud_weight_fingerprint_reuse: int = 40
    fraud_weight_time_to_purchase_immediate: int = 50
    fraud_weight_time_to_purchase_fast: int = 30
    fraud_weight_ip_velocity: int = 35
    fraud_fingerprint_threshold: int = 3
    fraud_ip_velocity_window_minutes: int = 10
    fraud_ip_velocity_threshold: int = 5

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"

    trusted_proxy_ip: str = ""

    ratelimit_enabled: bool = True

    idempotency_enabled: bool = True
    idempotency_lock_seconds: int = 30


settings = Settings()
