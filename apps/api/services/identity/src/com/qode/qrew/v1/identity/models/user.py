# defines the kyc status enum and the user table with its encrypted fields
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.core.database import Base


class KycStatus(enum.StrEnum):
    not_submitted = "not_submitted"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)

    email_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    phone_number_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    phone_number_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    hashed_password: Mapped[str] = mapped_column(String(255))

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    phone_number_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    email_verification_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    email_verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone_number_otp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_number_otp_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pending_phone_number_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    pending_phone_number_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    pending_phone_otp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_phone_otp_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pending_email_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    pending_email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pending_email_verification_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    pending_email_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    national_id_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    national_id_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    kyc_status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status"),
        default=KycStatus.not_submitted,
    )
    kyc_document_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    registration_ip: Mapped[str] = mapped_column(String(45))

    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    totp_secret_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_backup_codes_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    password_reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # decrypts the stored totp secret
    @property
    def totp_secret(self) -> str | None:
        if self.totp_secret_ciphertext is None:
            return None
        return pii_crypto.decrypt_bytes(self.totp_secret_ciphertext).decode()

    # encrypts the totp secret for storage
    @totp_secret.setter
    def totp_secret(self, value: str | None) -> None:
        if value is None:
            self.totp_secret_ciphertext = None
        else:
            self.totp_secret_ciphertext = pii_crypto.encrypt_bytes(value.encode())

    # decrypts the stored email
    @property
    def email(self) -> str:
        return pii_crypto.decrypt(self.email_ciphertext)

    # encrypts the email for storage and hashes it for lookup
    @email.setter
    def email(self, value: str) -> None:
        self.email_ciphertext = pii_crypto.encrypt(value)
        self.email_hash = pii_crypto.hash_lookup(value)

    # decrypts the stored phone number
    @property
    def phone_number(self) -> str:
        return pii_crypto.decrypt(self.phone_number_ciphertext)

    # encrypts the phone number for storage and hashes it for lookup
    @phone_number.setter
    def phone_number(self, value: str) -> None:
        self.phone_number_ciphertext = pii_crypto.encrypt(value)
        self.phone_number_hash = pii_crypto.hash_lookup(value)

    # decrypts the stored full name
    @property
    def full_name(self) -> str:
        return pii_crypto.decrypt(self.full_name_ciphertext)

    # encrypts the full name for storage
    @full_name.setter
    def full_name(self, value: str) -> None:
        self.full_name_ciphertext = pii_crypto.encrypt(value)

    # decrypts the stored pending email
    @property
    def pending_email(self) -> str | None:
        if self.pending_email_ciphertext is None:
            return None
        return pii_crypto.decrypt(self.pending_email_ciphertext)

    # encrypts the pending email for storage and hashes it for lookup
    @pending_email.setter
    def pending_email(self, value: str | None) -> None:
        if value is None:
            self.pending_email_ciphertext = None
            self.pending_email_hash = None
        else:
            self.pending_email_ciphertext = pii_crypto.encrypt(value)
            self.pending_email_hash = pii_crypto.hash_lookup(value)

    # decrypts the stored pending phone number
    @property
    def pending_phone_number(self) -> str | None:
        if self.pending_phone_number_ciphertext is None:
            return None
        return pii_crypto.decrypt(self.pending_phone_number_ciphertext)

    # encrypts the pending phone number for storage and hashes it for lookup
    @pending_phone_number.setter
    def pending_phone_number(self, value: str | None) -> None:
        if value is None:
            self.pending_phone_number_ciphertext = None
            self.pending_phone_number_hash = None
        else:
            self.pending_phone_number_ciphertext = pii_crypto.encrypt(value)
            self.pending_phone_number_hash = pii_crypto.hash_lookup(value)
