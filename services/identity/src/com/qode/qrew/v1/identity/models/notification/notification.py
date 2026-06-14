import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.identity.services.auth import pii_crypto
from com.qode.qrew.v1.identity.database import Base


class NotificationChannel(enum.StrEnum):
    email = "email"
    sms = "sms"


class NotificationStatus(enum.StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "identity"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"), nullable=False
    )
    template_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    destination_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.pending,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def destination(self) -> str:
        """Decrypts and returns the stored destination address."""
        return pii_crypto.decrypt(self.destination_ciphertext)

    @destination.setter
    def destination(self, value: str) -> None:
        self.destination_ciphertext = pii_crypto.encrypt(value)
