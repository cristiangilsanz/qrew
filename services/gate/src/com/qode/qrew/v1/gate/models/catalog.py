"""Read-only catalog schema models for the gate service."""
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.gate.database import Base


class Event(Base):
    """Minimal read-only projection of a catalog event."""

    __tablename__ = "events"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class OrganisationMember(Base):
    """Minimal read-only projection of a catalog organisation membership."""

    __tablename__ = "organisation_members"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
