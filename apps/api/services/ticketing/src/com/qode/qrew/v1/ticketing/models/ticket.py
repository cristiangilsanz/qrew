import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.ticketing.core.database import Base


class TicketState(enum.StrEnum):
    reserved = "reserved"
    issued = "issued"
    entry_pending = "entry_pending"
    used = "used"
    cancelled = "cancelled"
    expired = "expired"
    frozen = "frozen"
    flagged = "flagged"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_reservation_id", "reservation_id"),
        Index("ix_tickets_event_id", "event_id"),
        Index("ix_tickets_owner_user_id", "owner_user_id"),
        Index("ix_tickets_state", "state"),
        Index("ix_tickets_bound_device_id", "bound_device_id"),
        {"schema": "ticketing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bound_device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    state: Mapped[TicketState] = mapped_column(
        SAEnum(TicketState, native_enum=False, create_constraint=False),
        nullable=False,
        server_default=TicketState.reserved.value,
    )
    state_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    holder_dni: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
