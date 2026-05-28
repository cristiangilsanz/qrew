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
    host: str = "127.0.0.1"
    port: int = 8000
    base_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"

    access_jwt_private_key: str = ""
    setup_jwt_private_key: str = ""
    recovery_jwt_private_key: str = ""
    refresh_jwt_private_key: str = ""
    access_jwt_previous_public_keys: str = ""
    setup_jwt_previous_public_keys: str = ""
    recovery_jwt_previous_public_keys: str = ""
    refresh_jwt_previous_public_keys: str = ""
    access_token_expire_minutes: int = 30
    setup_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    email_verification_token_expire_hours: int = 24
    phone_number_otp_expire_minutes: int = 10

    kyc_auto_approve: bool = True
    national_id_encryption_key: str = "c2VrcmV0c2VrcmV0c2VrcmV0c2VrcmV0c2VrcmV0c2U="
    pii_encryption_key: str = "c2VrcmV0c2VrcmV0c2VrcmV0c2VrcmV0c2VrcmV0c2U="
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
    ios_team_id: str = ""
    ios_bundle_id: str = ""

    captcha_enabled: bool = False
    captcha_secret_key: str = "1x0000000000000000000000000000000AA"  # noqa: S105

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

    scanner_token_expire_hours: int = 12
    scanner_jwt_private_key: str = ""
    scanner_jwt_public_key: str = ""

    rp_id: str = "localhost"
    rp_name: str = "Qrew"
    rp_expected_origin: str = "http://localhost:3000"


settings = Settings()
