from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings import YamlConfigSettingsSource

_SERVICE_DIR = Path(__file__).parents[7]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=str(_SERVICE_DIR / "config" / "local.yaml"),
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-gateway"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    nats_url: str = ""

    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""
    scanner_jwt_private_key: str = ""
    jwt_audience: str = ""
    jwt_issuer: str = ""

    # Upstream service URLs (used by HTTP proxy)
    identity_url: str = "http://identity:8001"
    catalog_url: str = "http://catalog:8002"
    sales_url: str = "http://sales:8003"
    payments_url: str = "http://payments:8004"
    ticketing_url: str = "http://ticketing:8005"
    entry_url: str = "http://entry:8006"

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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )  # noqa: E501


settings = Settings()
