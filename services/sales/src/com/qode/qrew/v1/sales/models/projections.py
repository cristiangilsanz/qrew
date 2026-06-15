"""Read models for the sales service covering event state, inventory, and fraud detection."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.sales.core.database import Base


class EventContext(Base):
    """Projection of catalog event data needed for reservation validation."""

    __tablename__ = "event_context"
    __table_args__ = ({"schema": "sales"},)

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft")
    sale_starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sale_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_tickets_per_user: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    queue_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    queue_admit_rate_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="50"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TicketTypeInventory(Base):
    """Sales-owned inventory projection tracking capacity, reservations, and pricing per ticket type."""

    __tablename__ = "ticket_type_inventory"
    __table_args__ = ({"schema": "sales"},)

    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="EUR")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserAgeContext(Base):
    """Fraud projection: when did this user register?"""

    __tablename__ = "user_age_context"
    __table_args__ = ({"schema": "sales"},)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FingerprintContext(Base):
    """Fraud projection: how many distinct users share this fingerprint?"""

    __tablename__ = "fingerprint_context"
    __table_args__ = ({"schema": "sales"},)

    fingerprint_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    distinct_user_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
