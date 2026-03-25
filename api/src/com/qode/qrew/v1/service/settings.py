from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET_KEY = "sekret"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-api"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://qrew:qrew_secret@localhost:5432/qrew_db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = _DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 30

    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.environment == "production" and self.secret_key == _DEFAULT_SECRET_KEY:
            msg = "SECRET_KEY must be changed in production"
            raise ValueError(msg)
        return self


settings = Settings()
