import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.service.core.database import Base


class AuditAction(enum.StrEnum):
    REGISTER = "register"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGIN_LOCKED = "login_locked"
    LOGIN_UNLOCKED = "login_unlocked"
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
