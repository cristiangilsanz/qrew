"""2026_06_13_add_postgres_schemas

Revision ID: 6ec4ff49f815
Revises: f9a0b1c2d3e4
Create Date: 2026-06-13

Move tables into per-bounded-context Postgres schemas to prepare for service extraction.
The monolith connects with a superuser role during this phase so all schemas are visible.
Per-schema DB roles with restricted grants are added as each service is extracted.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "6ec4ff49f815"
down_revision: str | None = "a0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMAS = ["identity", "catalog", "sales", "payments", "ticketing", "gate", "audit"]

_TABLE_SCHEMA_MAP: list[tuple[str, str]] = [
    ("users", "identity"),
    ("sessions", "identity"),
    ("devices", "identity"),
    ("device_fingerprints", "identity"),
    ("passkey_credentials", "identity"),
    ("notifications", "identity"),
    ("organisations", "catalog"),
    ("organisation_members", "catalog"),
    ("venues", "catalog"),
    ("events", "catalog"),
    ("ticket_types", "catalog"),
    ("reservations", "sales"),
    ("payments", "payments"),
    ("tickets", "ticketing"),
    ("scanners", "gate"),
    ("audit_events", "audit"),
]


def upgrade() -> None:
    for schema in _SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    for table, schema in _TABLE_SCHEMA_MAP:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA {schema}")

    op.execute(
        "ALTER DATABASE qrew SET search_path TO "
        "identity, catalog, sales, payments, ticketing, gate, audit, public"
    )


def downgrade() -> None:
    op.execute("ALTER DATABASE qrew SET search_path TO public")

    for table, schema in reversed(_TABLE_SCHEMA_MAP):
        op.execute(f"ALTER TABLE {schema}.{table} SET SCHEMA public")

    for schema in reversed(_SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema}")
