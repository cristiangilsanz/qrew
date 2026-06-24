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

    app_name: str = "qrew-audit"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8007

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = ""

    internal_api_key: str = ""

    idempotency_enabled: bool = True
    idempotency_lock_seconds: int = 30

    ratelimit_enabled: bool = True

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"


settings = Settings()
