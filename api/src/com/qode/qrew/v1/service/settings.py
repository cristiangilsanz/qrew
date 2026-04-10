from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "qrew-api"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    base_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "sekret"  # noqa: S105
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    email_verification_token_expire_hours: int = 24
    phone_number_otp_expire_minutes: int = 10

    # Security
    hibp_enabled: bool = False

    # Cloudflare Turnstile
    captcha_enabled: bool = False
    captcha_secret_key: str = "1x0000000000000000000000000000000AA"  # noqa: S105

    # SMTP
    smtp_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""

    # Twilio
    twilio_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""


settings = Settings()
