import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.catalog.database import Base


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = (
        Index("ix_venues_city_country", "city", "country"),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    address_line: Mapped[str] = mapped_column(String(256), nullable=False)
    city: Mapped[str] = mapped_column(String(96), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    geofence_radius_m: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="200"
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
