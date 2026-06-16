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
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.catalog.core.database import Base


class EventStatus(enum.StrEnum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_events_time_window"),
        CheckConstraint("sale_starts_at < sale_ends_at", name="ck_events_sale_window"),
        CheckConstraint("sale_ends_at <= starts_at", name="ck_events_sale_before_start"),
        CheckConstraint(
            "max_tickets_per_user >= 1 AND max_tickets_per_user <= 20",
            name="ck_events_max_tickets",
        ),
        CheckConstraint(
            "queue_admit_rate_per_minute >= 1 AND queue_admit_rate_per_minute <= 600",
            name="ck_events_queue_admit_rate",
        ),
        Index("ix_events_organisation_id", "organisation_id"),
        Index("ix_events_venue_id", "venue_id"),
        Index("ix_events_status_starts_at", "status", "starts_at"),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.organisations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.venues.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sale_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sale_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_tickets_per_user: Mapped[int] = mapped_column(Integer, nullable=False, server_default="4")
    status: Mapped[EventStatus] = mapped_column(
        String(16), nullable=False, server_default=EventStatus.draft.value
    )
    organiser_name: Mapped[str] = mapped_column(String(128), nullable=False)
    venue_city: Mapped[str] = mapped_column(String(96), nullable=False)
    queue_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    queue_admit_rate_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="60"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
