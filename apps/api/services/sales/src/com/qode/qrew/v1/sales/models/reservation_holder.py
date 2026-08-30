# defines the table that names each reservation's ticket holders
import uuid

from sqlalchemy import CheckConstraint, Index, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.sales.core.database import Base
from com.qode.qrew.v1.sales.core.utils import pii as pii_crypto


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
    holder_dni_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # decrypts the stored identity document
    @property
    def holder_dni(self) -> str:
        return pii_crypto.decrypt(self.holder_dni_ciphertext)

    # encrypts the identity document for storage
    @holder_dni.setter
    def holder_dni(self, value: str) -> None:
        self.holder_dni_ciphertext = pii_crypto.encrypt(value)
