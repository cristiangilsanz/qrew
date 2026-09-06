# writes the fixture users devices and passkeys into identity

from __future__ import annotations

import asyncpg

from ..core import SeedConfig, Timeline, encrypt, hash_password, hash_pii, ident
from ..data import PASSWORD, Dataset

NAME = "identity"


# inserts every identity fixture row
async def write(
    conn: asyncpg.Connection, data: Dataset, when: Timeline, cfg: SeedConfig
) -> None:
    password = hash_password(PASSWORD)
    for person in data.people:
        await conn.execute(
            """
            INSERT INTO identity.users (
                id, full_name_ciphertext, email_ciphertext, email_hash,
                phone_number_ciphertext, phone_number_hash, hashed_password,
                email_verified, phone_number_verified, national_id_hash,
                national_id_number, national_id_type, kyc_ocr_result,
                kyc_status, terms_accepted_at, registration_ip, created_at, updated_at,
                is_active, is_admin
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::kyc_status,
                $15, $16, $17, $17, TRUE, $18
            )
            """,
            person.id,
            encrypt(cfg.fernet, person.name),
            encrypt(cfg.fernet, person.email),
            hash_pii(person.email),
            encrypt(cfg.fernet, person.phone),
            hash_pii(person.phone),
            password,
            person.verified,
            person.verified,
            hash_pii(person.national_id) if person.national_id else None,
            encrypt(cfg.fernet, person.national_id).decode()
            if person.national_id
            else None,
            person.document_type if person.national_id else None,
            person.ocr,
            person.kyc,
            when.days(-30),
            "127.0.0.1",
            when.days(-30),
            person.admin,
        )

    for person_key, device_name in data.devices:
        await conn.execute(
            """
            INSERT INTO identity.devices (id, user_id, name, public_key, created_at,
                                          last_seen_at, attested_at,
                                          attestation_platform)
            VALUES ($1, $2, $3, $4, $5, $6, $6, 'android')
            """,
            ident("device", person_key),
            data.person(person_key).id,
            device_name,
            f"seeded-device-key-{person_key}".encode(),
            when.days(-20),
            when.hours(-1),
        )

    for person in data.people:
        if not person.verified:
            continue
        await conn.execute(
            """
            INSERT INTO identity.passkey_credentials (
                id, user_id, credential_id, public_key, sign_count, aaguid, name,
                last_used_at, created_at
            ) VALUES ($1, $2, $3, $4, 0, $5, 'Seeded passkey', $6, $7)
            """,
            ident("passkey", person.key),
            person.id,
            f"seeded-credential-{person.key}".encode(),
            f"seeded-passkey-key-{person.key}".encode(),
            "00000000-0000-0000-0000-000000000000",
            when.hours(-2),
            when.days(-30),
        )
