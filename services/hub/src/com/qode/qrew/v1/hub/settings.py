from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-hub"
    version: str = "0.1.0"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8008

    nats_url: str = "nats://localhost:4222"

    # Shared with identity — same ES256 key material
    access_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""

    # Scanner JWT (gate-issued, verified independently)
    scanner_jwt_private_key: str = ""

    ws_heartbeat_seconds: int = 30
    ws_pong_timeout_seconds: int = 10
    ws_send_queue_size: int = 64


settings = Settings()
