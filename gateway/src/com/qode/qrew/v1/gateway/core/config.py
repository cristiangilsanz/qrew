from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-gateway"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8008

    nats_url: str = ""

    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""
    scanner_jwt_private_key: str = ""
    jwt_audience: str = ""
    jwt_issuer: str = ""

    ws_heartbeat_seconds: int = 30
    ws_pong_timeout_seconds: int = 10

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"

    redis_url: str = "redis://localhost:6379/0"
    idempotency_enabled: bool = True
    idempotency_lock_seconds: int = 30
    ratelimit_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept both JSON arrays and comma-separated strings from env vars."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
