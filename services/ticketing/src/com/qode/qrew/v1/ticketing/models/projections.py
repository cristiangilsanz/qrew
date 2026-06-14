import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.ticketing.database import Base


class EventVenueContext(Base):
    """Read-only local projection of event and venue data used during gate evaluation."""

    __tablename__ = "event_venue_context"
    __table_args__ = ({"schema": "ticketing"},)

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="draft"
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6), nullable=False, server_default="0"
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6), nullable=False, server_default="0"
    )
    geofence_radius_m: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="200"
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="UTC")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DeviceContext(Base):
    """Read-only local projection of device attestation and revocation state."""

    __tablename__ = "device_context"
    __table_args__ = (
        Index("ix_device_context_user_id", "user_id"),
        {"schema": "ticketing"},
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
