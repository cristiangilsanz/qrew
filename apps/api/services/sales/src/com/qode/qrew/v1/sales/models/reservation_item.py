# defines the table that holds how many tickets of each type a reservation covers
import uuid

from sqlalchemy import CheckConstraint, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.sales.core.database import Base


class ReservationItem(Base):
    __tablename__ = "reservation_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_reservation_items_quantity"),
        UniqueConstraint(
            "reservation_id", "ticket_type_id", name="uq_reservation_items_reservation_tier"
        ),
        Index("ix_reservation_items_reservation_id", "reservation_id"),
        {"schema": "sales"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
