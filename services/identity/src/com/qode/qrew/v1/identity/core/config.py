from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "qrew-identity"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8006
    base_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = ""

    access_jwt_private_key: str = ""
    setup_jwt_private_key: str = ""
    recovery_jwt_private_key: str = ""
    refresh_jwt_private_key: str = ""
    queue_jwt_private_key: str = ""
    ticket_qr_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""
    setup_jwt_previous_public_keys: str = ""
    recovery_jwt_previous_public_keys: str = ""
    refresh_jwt_previous_public_keys: str = ""
    queue_jwt_previous_public_keys: str = ""
    ticket_qr_jwt_previous_public_keys: str = ""
    access_token_expire_minutes: int = 30
    setup_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    email_verification_token_expire_hours: int = 24
    phone_number_otp_expire_minutes: int = 10

    kyc_auto_approve: bool = False
    national_id_encryption_key: str = ""
    pii_encryption_key: str = ""
    pii_encryption_previous_keys: str = ""

    fingerprint_multi_account_threshold: int = 2

    geoip_db_path: str = "GeoLite2-City.mmdb"
    anomaly_impossible_travel_kmh: float = 1000.0
    anomaly_concurrent_window_minutes: int = 5
    anomaly_kill_sessions_on_detection: bool = False

    hibp_enabled: bool = False

    login_max_attempts: int = 5
    login_lockout_base_seconds: int = 300

    max_sessions_per_user: int = 5

    attestation_enabled: bool = False
    attestation_dev_bypass: bool = True
    android_package_name: str = ""
    android_app_cert_digest_sha256: str = ""

    captcha_enabled: bool = False
    captcha_secret_key: str = ""

    smtp_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""

    twilio_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    rp_id: str = "localhost"
    rp_name: str = "Qrew"
    rp_expected_origin: str = "http://localhost:3000"

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"

    ratelimit_audit_debounce_seconds: int = 60

    idempotency_enabled: bool = True
    idempotency_lock_seconds: int = 60

    storage_root: str = "./var/storage"
    storage_signing_key: str = ""
    storage_signed_url_ttl_seconds: int = 300
    kyc_document_retention_days: int = 30

    notification_enabled: bool = True
    notification_max_attempts: int = 5

    outbox_batch_size: int = 50
    outbox_max_attempts: int = 5
    outbox_backoff_delays_seconds: list[int] = [1, 5, 25, 125, 625]

    internal_api_key: str = ""


settings = Settings()
