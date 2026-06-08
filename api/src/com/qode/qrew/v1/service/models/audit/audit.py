import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.service.core.infra.database import Base


class AuditAction(enum.StrEnum):
    REGISTER = "register"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGIN_LOCKED = "login_locked"
    LOGIN_UNLOCKED = "login_unlocked"
    LOGIN_COMPROMISED_PASSWORD = "login_compromised_password"  # noqa: S105
    SESSION_EVICTED = "session_evicted"
    ACCOUNT_DELETED = "account_deleted"
    DEVICE_ATTESTED = "device_attested"
    DEVICE_ATTESTATION_FAILED = "device_attestation_failed"
    LOGOUT = "logout"
    VERIFY_EMAIL = "verify_email"
    VERIFY_PHONE = "verify_phone"
    KYC_UPLOADED = "kyc_uploaded"
    KYC_REVIEWED = "kyc_reviewed"
    PASSKEY_REGISTERED = "passkey_registered"
    PASSKEY_AUTHENTICATED = "passkey_authenticated"
    PASSKEY_DELETED = "passkey_deleted"
    PASSKEY_RENAMED = "passkey_renamed"
    TOKEN_REFRESHED = "token_refreshed"  # noqa: S105
    TOKEN_THEFT_DETECTED = "token_theft_detected"  # noqa: S105
    REFRESH_SIGNATURE_INVALID = "refresh_signature_invalid"
    SETUP_COMPLETED = "setup_completed"
    PASSWORD_CHANGED = "password_changed"  # noqa: S105
    EMAIL_CHANGE_REQUESTED = "email_change_requested"
    EMAIL_CHANGE_CONFIRMED = "email_change_confirmed"
    PHONE_CHANGE_REQUESTED = "phone_change_requested"
    PHONE_CHANGE_CONFIRMED = "phone_change_confirmed"
    FINGERPRINT_MULTI_ACCOUNT_FLAG = "fingerprint_multi_account_flag"
    FINGERPRINT_HEADLESS_FLAG = "fingerprint_headless_flag"
    RECOVERY_BEGIN = "recovery_begin"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    LOGIN_ANOMALY_DETECTED = "login_anomaly_detected"
    DEVICE_BIND = "device_bind"
    DEVICE_REVOKE = "device_revoke"
    DEVICE_REVOKE_ALL = "device_revoke_all"
    PASSKEY_REASSERTED = "passkey_reasserted"
    SCANNER_CREATED = "scanner_created"
    SCANNER_ROTATED = "scanner_rotated"
    SCANNER_DEACTIVATED = "scanner_deactivated"
    GENESIS = "genesis"
    AUDIT_CHAIN_VERIFIED = "audit_chain_verified"
    AUDIT_CHAIN_TAMPERED = "audit_chain_tampered"
    EXPIRED_TOKENS_CLEANED = "expired_tokens_cleaned"
    RATE_LIMIT_HIT = "rate_limit_hit"
    NOTIFICATION_FAILED = "notification_failed"
    ORGANISATION_CREATED = "organisation_created"
    ORGANISATION_MEMBER_ADDED = "organisation_member_added"
    ORGANISATION_MEMBER_REMOVED = "organisation_member_removed"
    VENUE_CREATED = "venue_created"
    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    EVENT_PUBLISHED = "event_published"
    EVENT_CANCELLED = "event_cancelled"
    TICKET_TYPE_CREATED = "ticket_type_created"  # noqa: S105
    TICKET_TYPE_UPDATED = "ticket_type_updated"  # noqa: S105
    TICKET_TYPE_DELETED = "ticket_type_deleted"  # noqa: S105
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_EXPIRED = "reservation_expired"
    QUEUE_JOINED = "queue_joined"
    QUEUE_REDEEMED = "queue_redeemed"
    QUEUE_REDEEM_FAILED = "queue_redeem_failed"
    RESERVATION_FLAGGED = "reservation_flagged"
    RESERVATION_BLOCKED = "reservation_blocked"
    PAYMENT_INITIATED = "payment_initiated"  # noqa: S105
    PAYMENT_SUCCEEDED = "payment_succeeded"  # noqa: S105
    PAYMENT_FAILED = "payment_failed"  # noqa: S105
    WEBHOOK_INVALID_SIGNATURE = "webhook_invalid_signature"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_fingerprint_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    prev_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32), nullable=True)
    hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
