from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-api"
    version: str = "0.1.0"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "sekret"
    access_token_expire_minutes: int = 30

    host: str = "127.0.0.1"
    port: int = 8000

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


settings = Settings()
