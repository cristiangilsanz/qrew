import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.service.core.database import Base


class KycStatus(enum.StrEnum):
    not_submitted = "not_submitted"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    full_name: Mapped[str] = mapped_column(String(255))

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    hashed_password: Mapped[str] = mapped_column(String(255))

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    phone_number_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    email_verification_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    email_verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone_number_otp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone_number_otp_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pending_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pending_phone_otp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    pending_phone_otp_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pending_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pending_email_verification_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    pending_email_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    national_id_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kyc_status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status"),
        default=KycStatus.not_submitted,
    )

    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    registration_ip: Mapped[str] = mapped_column(String(45))

    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
