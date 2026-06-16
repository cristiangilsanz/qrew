import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.catalog.core.database import Base


class OrganisationRole(enum.StrEnum):
    member = "member"
    manager = "manager"
    owner = "owner"


_ROLE_RANK = {
    OrganisationRole.member: 0,
    OrganisationRole.manager: 1,
    OrganisationRole.owner: 2,
}


def role_rank(role: OrganisationRole) -> int:
    return _ROLE_RANK[role]


class Organisation(Base):
    __tablename__ = "organisations"
    __table_args__ = {"schema": "catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrganisationMember(Base):
    __tablename__ = "organisation_members"
    __table_args__ = (
        UniqueConstraint("organisation_id", "user_id", name="uq_organisation_members_org_user"),
        {"schema": "catalog"},
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.organisations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[OrganisationRole] = mapped_column(
        Enum(OrganisationRole, name="organisation_role"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
