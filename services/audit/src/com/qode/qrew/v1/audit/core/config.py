from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-audit"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8007

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    nats_url: str = "nats://localhost:4222"

    internal_api_key: str = "dev-internal-secret"

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_environment: str = "dev"


settings = Settings()
