import uuid

from sqlalchemy import CheckConstraint, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.sales.core.database import Base


class ReservationHolder(Base):
    __tablename__ = "reservation_holders"
    __table_args__ = (
        CheckConstraint("position >= 1", name="ck_reservation_holders_position"),
        UniqueConstraint(
            "reservation_id", "position", name="uq_reservation_holders_reservation_position"
        ),
        Index("ix_reservation_holders_reservation_id", "reservation_id"),
        {"schema": "sales"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    holder_dni: Mapped[str] = mapped_column(String(50), nullable=False)
