"""2026_05_08_add_kyc_fields_and_passkey_credentials

Revision ID: 3abe87e2c49f
Revises: 393549af2f17
Create Date: 2026-05-08 01:04:19.945785

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3abe87e2c49f"
down_revision: str | None = "393549af2f17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


kyc_status_enum = sa.Enum(
    "not_submitted", "pending", "approved", "rejected", name="kyc_status"
)


def upgrade() -> None:
    kyc_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "passkey_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False),
        sa.Column("aaguid", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_passkey_credentials_credential_id"),
        "passkey_credentials",
        ["credential_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_passkey_credentials_user_id"),
        "passkey_credentials",
        ["user_id"],
        unique=False,
    )
    op.add_column(
        "users", sa.Column("national_id_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "kyc_status",
            kyc_status_enum,
            nullable=False,
            server_default="not_submitted",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "kyc_status")
    op.drop_column("users", "national_id_hash")
    op.drop_index(
        op.f("ix_passkey_credentials_user_id"), table_name="passkey_credentials"
    )
    op.drop_index(
        op.f("ix_passkey_credentials_credential_id"), table_name="passkey_credentials"
    )
    op.drop_table("passkey_credentials")
    kyc_status_enum.drop(op.get_bind(), checkfirst=True)
