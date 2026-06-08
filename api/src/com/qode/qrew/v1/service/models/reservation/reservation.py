import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.service.core.infra.database import Base


class ReservationStatus(enum.StrEnum):
    reserved = "reserved"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_reservations_quantity"),
        Index("ix_reservations_user_id", "user_id"),
        Index("ix_reservations_event_id", "event_id"),
        Index(
            "ix_reservations_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ticket_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        String(16),
        nullable=False,
        server_default=ReservationStatus.reserved.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    requires_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
