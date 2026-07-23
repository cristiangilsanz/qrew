import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.sales.core.database import Base


class MarketListingState(enum.StrEnum):
    available = "available"
    assigned = "assigned"
    completed = "completed"
    cancelled = "cancelled"


class MarketAssignmentState(enum.StrEnum):
    pending = "pending"
    paid = "paid"
    expired = "expired"
    declined = "declined"


class MarketQueueEntry(Base):
    __tablename__ = "market_queue_entries"
    __table_args__ = (
        Index(
            "ix_market_queue_entries_event_id_active",
            "event_id",
            postgresql_where="left_at IS NULL",
        ),
        Index("ix_market_queue_entries_user_id", "user_id"),
        {"schema": "sales"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tiebreak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketListing(Base):
    __tablename__ = "market_listings"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_market_listings_price"),
        CheckConstraint(
            "state IN ('available', 'assigned', 'completed', 'cancelled')",
            name="ck_market_listings_state",
        ),
        Index("ix_market_listings_event_id_state", "event_id", "state"),
        Index("ix_market_listings_seller_user_id", "seller_user_id"),
        {"schema": "sales"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    seller_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="EUR")
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=MarketListingState.available.value
    )
    listed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketAssignment(Base):
    __tablename__ = "market_assignments"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'paid', 'expired', 'declined')",
            name="ck_market_assignments_state",
        ),
        Index("ix_market_assignments_listing_id", "listing_id"),
        Index("ix_market_assignments_buyer_user_id", "buyer_user_id"),
        {"schema": "sales"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.market_listings.id"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    holder_dni: Mapped[str | None] = mapped_column(String(50), nullable=True)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=MarketAssignmentState.pending.value
    )
