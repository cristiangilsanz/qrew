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
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8006
    base_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    database_url: str = "postgresql+asyncpg://postgres:sekret@localhost:5432/qrew"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"

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

    kyc_auto_approve: bool = False  #!
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

    rp_id: str = "localhost"
    rp_name: str = "Qrew"
    rp_expected_origin: str = "http://localhost:3000"

    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_environment: str = "dev"

    ratelimit_enabled: bool = True
    ratelimit_fail_open: bool = True
    ratelimit_audit_debounce_seconds: int = 60

    idempotency_enabled: bool = True
    idempotency_default_ttl_seconds: int = 86_400
    idempotency_lock_seconds: int = 60

    ws_enabled: bool = True
    ws_heartbeat_seconds: int = 30
    ws_pong_timeout_seconds: int = 10
    ws_send_queue_size: int = 64

    storage_root: str = "./var/storage"
    storage_signing_key: str = "c2VrcmV0c3RvcmFnZXNpZ25pbmdrZXlmb3JkZXY="
    storage_signed_url_ttl_seconds: int = 300
    kyc_document_retention_days: int = 30

    notification_enabled: bool = True
    notification_max_attempts: int = 5

    search_default_limit: int = 20
    search_max_limit: int = 100

    locking_default_ttl_seconds: float = 10.0
    locking_default_retry_attempts: int = 3
    locking_default_retry_delay_ms: int = 200

    outbox_batch_size: int = 50
    outbox_max_attempts: int = 5
    outbox_backoff_delays_seconds: list[int] = [1, 5, 25, 125, 625]

    reservation_ttl_seconds: int = 600
    reservation_sweep_batch_size: int = 200

    payments_default_currency: str = "EUR"

    fraud_signals_enabled: bool = True
    fraud_score_review_threshold: int = 40
    fraud_score_block_threshold: int = 70
    fraud_ip_velocity_window_seconds: int = 60
    fraud_ip_velocity_threshold: int = 10
    fraud_fingerprint_lookback_hours: int = 24
    fraud_fingerprint_threshold: int = 2
    fraud_weight_account_age_recent: int = 40
    fraud_weight_account_age_young: int = 20
    fraud_weight_voip_phone: int = 25
    fraud_weight_time_to_purchase_immediate: int = 50
    fraud_weight_time_to_purchase_fast: int = 30
    fraud_weight_ip_velocity: int = 35
    fraud_weight_fingerprint_reuse: int = 30
    fraud_voip_phone_prefixes: list[str] = [
        "+1844",
        "+1855",
        "+1866",
        "+1877",
        "+1888",
    ]

    queue_redeem_window_seconds: int = 90
    queue_reservation_window_seconds: int = 120
    queue_admit_default_rate_per_minute: int = 60
    queue_join_lead_seconds: int = 900

    ticket_qr_ttl_seconds: int = 20
    ticket_qr_reassert_window_seconds: int = 30
    ticket_qr_mint_audit_sample_rate: int = 10
    ticket_qr_attestation_max_age_hours: int = 24
    ticket_qr_audience: str = "qrew.scan"
    ticket_qr_stream_max_seconds: int = 1800

    internal_api_key: str = "dev-internal-secret"

    entry_replay_grace_seconds: int = 10
    entry_stats_cache_ttl_seconds: int = 5
    entry_stats_default_window_hours: int = 24


settings = Settings()
