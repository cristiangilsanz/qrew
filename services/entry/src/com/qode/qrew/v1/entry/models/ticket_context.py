import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.entry.core.database import Base


class TicketState(enum.StrEnum):
    reserved = "reserved"
    issued = "issued"
    entry_pending = "entry_pending"
    used = "used"
    cancelled = "cancelled"
    frozen = "frozen"
    flagged = "flagged"


class TicketContext(Base):
    """Read-only local projection of ticket state, updated via event subscription."""

    __tablename__ = "ticket_contexts"
    __table_args__ = {"schema": "entry"}

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    bound_device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
