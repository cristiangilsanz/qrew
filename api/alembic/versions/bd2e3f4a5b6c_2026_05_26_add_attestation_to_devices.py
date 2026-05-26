"""2026_05_26_add_attestation_to_devices

Revision ID: bd2e3f4a5b6c
Revises: ad1e2f3a4b5c
Create Date: 2026-05-26 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bd2e3f4a5b6c"
down_revision: str | None = "ad1e2f3a4b5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("attestation_platform", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("devices", "attestation_platform")
    op.drop_column("devices", "attested_at")
