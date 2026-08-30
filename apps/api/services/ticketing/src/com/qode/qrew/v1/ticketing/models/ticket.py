# defines the ticket state enum and the ticket table
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Index, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.ticketing.core.database import Base
from com.qode.qrew.v1.ticketing.core.utils import pii as pii_crypto


class TicketState(enum.StrEnum):
    reserved = "reserved"
    issued = "issued"
    scanning = "scanning"
    redeemed = "redeemed"
    cancelled = "cancelled"
    expired = "expired"
    on_sale = "on_sale"
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
    holder_dni_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # decrypts the stored identity document
    @property
    def holder_dni(self) -> str | None:
        if self.holder_dni_ciphertext is None:
            return None
        return pii_crypto.decrypt(self.holder_dni_ciphertext)

    # encrypts the identity document for storage
    @holder_dni.setter
    def holder_dni(self, value: str | None) -> None:
        self.holder_dni_ciphertext = None if value is None else pii_crypto.encrypt(value)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
