"""2026_05_29_encrypt_user_pii_columns

Revision ID: c4d5e6f7a8b9
Revises: bd2e3f4a5b6c
Create Date: 2026-05-29

"""

import hashlib
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "bd2e3f4a5b6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_HASH_PREFIX = b"qrew-pii-v1:"


def _fernet() -> Fernet:
    key = os.environ.get("PII_ENCRYPTION_KEY") or os.environ.get(
        "NATIONAL_ID_ENCRYPTION_KEY"
    )
    if not key:
        raise RuntimeError("PII_ENCRYPTION_KEY must be set in the environment")
    return Fernet(key.encode())


def _hash_lookup(plaintext: str) -> str:
    normalised = plaintext.strip().lower().encode()
    return hashlib.sha256(_HASH_PREFIX + normalised).hexdigest()


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("email_ciphertext", sa.LargeBinary(), nullable=True)
    )
    op.add_column("users", sa.Column("email_hash", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("phone_number_ciphertext", sa.LargeBinary(), nullable=True)
    )
    op.add_column("users", sa.Column("phone_number_hash", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("full_name_ciphertext", sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("pending_email_ciphertext", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "users", sa.Column("pending_email_hash", sa.String(64), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("pending_phone_number_ciphertext", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "users", sa.Column("pending_phone_number_hash", sa.String(64), nullable=True)
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, email, phone_number, full_name, pending_email,"
            " pending_phone_number FROM users"
        )
    ).fetchall()

    if rows:
        fernet = _fernet()
        for row in rows:
            (
                user_id,
                email,
                phone_number,
                full_name,
                pending_email,
                pending_phone_number,
            ) = row
            bind.execute(
                sa.text(
                    "UPDATE users SET"
                    " email_ciphertext = :email_ct, email_hash = :email_h,"
                    " phone_number_ciphertext = :phone_ct, phone_number_hash = :phone_h,"
                    " full_name_ciphertext = :name_ct,"
                    " pending_email_ciphertext = :pending_email_ct,"
                    " pending_email_hash = :pending_email_h,"
                    " pending_phone_number_ciphertext = :pending_phone_ct,"
                    " pending_phone_number_hash = :pending_phone_h"
                    " WHERE id = :id"
                ),
                {
                    "id": user_id,
                    "email_ct": fernet.encrypt(email.encode()),
                    "email_h": _hash_lookup(email),
                    "phone_ct": fernet.encrypt(phone_number.encode()),
                    "phone_h": _hash_lookup(phone_number),
                    "name_ct": fernet.encrypt(full_name.encode()),
                    "pending_email_ct": (
                        fernet.encrypt(pending_email.encode())
                        if pending_email
                        else None
                    ),
                    "pending_email_h": (
                        _hash_lookup(pending_email) if pending_email else None
                    ),
                    "pending_phone_ct": (
                        fernet.encrypt(pending_phone_number.encode())
                        if pending_phone_number
                        else None
                    ),
                    "pending_phone_h": (
                        _hash_lookup(pending_phone_number)
                        if pending_phone_number
                        else None
                    ),
                },
            )

    op.alter_column("users", "email_ciphertext", nullable=False)
    op.alter_column("users", "email_hash", nullable=False)
    op.alter_column("users", "phone_number_ciphertext", nullable=False)
    op.alter_column("users", "phone_number_hash", nullable=False)
    op.alter_column("users", "full_name_ciphertext", nullable=False)

    op.create_index(op.f("ix_users_email_hash"), "users", ["email_hash"], unique=True)
    op.create_index(
        op.f("ix_users_phone_number_hash"),
        "users",
        ["phone_number_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_users_pending_email_hash"),
        "users",
        ["pending_email_hash"],
    )
    op.create_index(
        op.f("ix_users_pending_phone_number_hash"),
        "users",
        ["pending_phone_number_hash"],
    )

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_index("ix_users_pending_email_verification_token", table_name="users")
    op.create_index(
        op.f("ix_users_pending_email_verification_token"),
        "users",
        ["pending_email_verification_token"],
    )

    op.drop_column("users", "email")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "full_name")
    op.drop_column("users", "pending_email")
    op.drop_column("users", "pending_phone_number")


def downgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("pending_email", sa.String(255), nullable=True))
    op.add_column(
        "users", sa.Column("pending_phone_number", sa.String(20), nullable=True)
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, email_ciphertext, phone_number_ciphertext,"
            " full_name_ciphertext, pending_email_ciphertext,"
            " pending_phone_number_ciphertext FROM users"
        )
    ).fetchall()

    if rows:
        fernet = _fernet()
        for row in rows:
            (
                user_id,
                email_ct,
                phone_ct,
                name_ct,
                pending_email_ct,
                pending_phone_ct,
            ) = row
            bind.execute(
                sa.text(
                    "UPDATE users SET email = :e, phone_number = :p,"
                    " full_name = :n, pending_email = :pe,"
                    " pending_phone_number = :pp WHERE id = :id"
                ),
                {
                    "id": user_id,
                    "e": fernet.decrypt(bytes(email_ct)).decode(),
                    "p": fernet.decrypt(bytes(phone_ct)).decode(),
                    "n": fernet.decrypt(bytes(name_ct)).decode(),
                    "pe": (
                        fernet.decrypt(bytes(pending_email_ct)).decode()
                        if pending_email_ct
                        else None
                    ),
                    "pp": (
                        fernet.decrypt(bytes(pending_phone_ct)).decode()
                        if pending_phone_ct
                        else None
                    ),
                },
            )

    op.alter_column("users", "email", nullable=False)
    op.alter_column("users", "phone_number", nullable=False)
    op.alter_column("users", "full_name", nullable=False)

    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_index(
        "ix_users_pending_email_verification_token",
        "users",
        ["pending_email_verification_token"],
    )

    op.drop_index(op.f("ix_users_pending_phone_number_hash"), table_name="users")
    op.drop_index(op.f("ix_users_pending_email_hash"), table_name="users")
    op.drop_index(op.f("ix_users_phone_number_hash"), table_name="users")
    op.drop_index(op.f("ix_users_email_hash"), table_name="users")

    op.drop_column("users", "pending_phone_number_hash")
    op.drop_column("users", "pending_phone_number_ciphertext")
    op.drop_column("users", "pending_email_hash")
    op.drop_column("users", "pending_email_ciphertext")
    op.drop_column("users", "full_name_ciphertext")
    op.drop_column("users", "phone_number_hash")
    op.drop_column("users", "phone_number_ciphertext")
    op.drop_column("users", "email_hash")
    op.drop_column("users", "email_ciphertext")
