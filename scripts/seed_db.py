#!/usr/bin/env python3
# ruff: noqa: E501
"""
Seed the database with test data for development.

Run with:
    just db-seed

Creates:
  Users (password Password123! / AdminPass1!):
    - alice@qrew.dev  (regular, KYC approved)
    - bob@qrew.dev    (regular, KYC pending)
    - admin@qrew.dev  (admin)

  Organisation: Qrew Events (admin=owner, alice=manager)

  Venues: WiZink Center (Madrid), Palau Sant Jordi (Barcelona)

  Events:
    - Midnight Festival 2025   (past, sale ended)
    - Summer Beats 2026        (upcoming, sale open now)
    - Techno Underground 2026  (upcoming, sale opens Sep 2026)

  Tickets for alice: 1 used (past event) + 2 issued (Summer Beats)
  Reservation for bob: 1 reserved GA (Summer Beats)
"""

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import yaml
from cryptography.fernet import Fernet, MultiFernet
from passlib.context import CryptContext

REPO_ROOT = Path(__file__).resolve().parent.parent
IDENTITY_CFG = REPO_ROOT / "apps/api/services/identity/config/local.yaml"

# ── PII helpers ──────────────────────────────────────────────────────────────


def _make_fernet(key: str, prev: str = "") -> MultiFernet:
    keys = [Fernet(key.encode())]
    for raw in prev.splitlines():
        k = raw.strip()
        if k:
            keys.append(Fernet(k.encode()))
    return MultiFernet(keys)


def _enc(fernet: MultiFernet, value: str) -> bytes:
    return fernet.encrypt(value.encode())


def _hash(value: str) -> str:
    prefix = b"qrew-pii-v1:"
    return hashlib.sha256(prefix + value.strip().lower().encode()).hexdigest()


_pwd = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def _hpw(password: str) -> str:
    return _pwd.hash(password)


# ── DB URL ───────────────────────────────────────────────────────────────────


def _pg_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


# ── Seed ─────────────────────────────────────────────────────────────────────


async def seed() -> None:
    cfg = yaml.safe_load(IDENTITY_CFG.read_text())
    fernet = _make_fernet(
        cfg["pii_encryption_key"],
        cfg.get("pii_encryption_previous_keys", ""),
    )
    conn = await asyncpg.connect(_pg_url(cfg["database_url"]))
    try:
        await _run(conn, fernet)
    finally:
        await conn.close()


async def _run(conn: asyncpg.Connection, fernet: MultiFernet) -> None:

    now = datetime.now(UTC)

    # ── Fixed UUIDs ──────────────────────────────────────────────────────────

    user_alice = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
    user_bob = uuid.UUID("bbbbbbbb-0002-0002-0002-000000000002")
    user_admin = uuid.UUID("cccccccc-0003-0003-0003-000000000003")

    org_id = uuid.UUID("00000000-aaaa-aaaa-aaaa-000000000001")

    venue_mad = uuid.UUID("11111111-0001-0001-0001-000000000001")
    venue_bcn = uuid.UUID("11111111-0002-0002-0002-000000000002")

    event_past = uuid.UUID("22222222-0001-0001-0001-000000000001")
    event_now = uuid.UUID("22222222-0002-0002-0002-000000000002")
    event_future = uuid.UUID("22222222-0003-0003-0003-000000000003")

    tt_past_ga = uuid.UUID("33333333-0001-0001-0001-000000000001")
    tt_past_vip = uuid.UUID("33333333-0002-0002-0002-000000000002")
    tt_now_ga = uuid.UUID("33333333-0003-0003-0003-000000000003")
    tt_now_vip = uuid.UUID("33333333-0004-0004-0004-000000000004")
    tt_now_artist = uuid.UUID("33333333-0005-0005-0005-000000000005")
    tt_fut_early = uuid.UUID("33333333-0006-0006-0006-000000000006")
    tt_fut_ga = uuid.UUID("33333333-0007-0007-0007-000000000007")

    res_alice_past = uuid.UUID("44444444-0001-0001-0001-000000000001")
    res_alice_now = uuid.UUID("44444444-0002-0002-0002-000000000002")
    res_bob_now = uuid.UUID("44444444-0003-0003-0003-000000000003")

    tk_alice_past = uuid.UUID("55555555-0001-0001-0001-000000000001")
    tk_alice_now1 = uuid.UUID("55555555-0002-0002-0002-000000000002")
    tk_alice_now2 = uuid.UUID("55555555-0003-0003-0003-000000000003")
    tk_bob_now = uuid.UUID("55555555-0004-0004-0004-000000000004")

    # Market test data (event with sale ended + starts 30 days from now)
    event_market = uuid.UUID("22222222-0004-0004-0004-000000000004")
    tt_market_ga = uuid.UUID("33333333-0008-0008-0008-000000000008")
    res_admin_market = uuid.UUID("44444444-0006-0006-0006-000000000006")
    res_alice_market = uuid.UUID("44444444-0007-0007-0007-000000000007")
    tk_admin_market = uuid.UUID("55555555-0007-0007-0007-000000000007")  # issued — test Sale btn
    tk_alice_market = uuid.UUID("55555555-0008-0008-0008-000000000008")  # frozen — test My Listings
    market_listing_id = uuid.UUID("66666666-0001-0001-0001-000000000001")
    market_assignment_id = uuid.UUID("77777777-0001-0001-0001-000000000001")

    # ── Truncate all seed tables ──────────────────────────────────────────────
    print("  Truncating tables…")
    await conn.execute("""
        TRUNCATE
            sales.market_assignments,
            sales.market_listings,
            sales.market_queue_entries,
            ticketing.tickets,
            ticketing.event_venue_context,
            ticketing.device_context,
            sales.reservation_holders,
            sales.reservations,
            sales.event_context,
            sales.ticket_type_inventory,
            sales.user_age_context,
            sales.fingerprint_context,
            catalog.ticket_types,
            catalog.events,
            catalog.organisation_members,
            catalog.venues,
            catalog.organisations,
            identity.passkey_credentials,
            identity.users
        CASCADE
    """)

    # ── Users ─────────────────────────────────────────────────────────────────
    print("  Creating users…")

    users = [
        {
            "id": user_alice,
            "email": "alice@qrew.dev",
            "full_name": "Alice Dev",
            "phone": "+34600000001",
            "password": "Password123!",
            "kyc_status": "approved",
            "is_admin": False,
        },
        {
            "id": user_bob,
            "email": "bob@qrew.dev",
            "full_name": "Bob Dev",
            "phone": "+34600000002",
            "password": "Password123!",
            "kyc_status": "pending",
            "is_admin": False,
        },
        {
            "id": user_admin,
            "email": "admin@qrew.dev",
            "full_name": "Admin User",
            "phone": "+34600000003",
            "password": "AdminPass1!",
            "kyc_status": "approved",
            "is_admin": True,
        },
    ]

    for u in users:
        await conn.execute(
            """
            INSERT INTO identity.users (
                id,
                full_name_ciphertext,
                email_ciphertext, email_hash,
                phone_number_ciphertext, phone_number_hash,
                hashed_password,
                email_verified, phone_number_verified,
                kyc_status,
                terms_accepted_at, registration_ip,
                is_active, is_admin,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9,
                $10::kyc_status,
                $11, $12, $13, $14, $15, $16
            )
            """,
            u["id"],
            _enc(fernet, u["full_name"]),
            _enc(fernet, u["email"]),
            _hash(u["email"]),
            _enc(fernet, u["phone"]),
            _hash(u["phone"]),
            _hpw(u["password"]),
            True,  # email_verified
            True,  # phone_number_verified
            u["kyc_status"],
            now,  # terms_accepted_at
            "127.0.0.1",
            True,  # is_active
            u["is_admin"],
            now,
            now,
        )

    # ── Organisation ──────────────────────────────────────────────────────────
    print("  Creating organisation…")

    await conn.execute(
        """
        INSERT INTO catalog.organisations (id, slug, name, description, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        org_id,
        "qrew-events",
        "Qrew Events",
        "Official Qrew Events organisation for development testing.",
        now,
        now,
    )
    await conn.execute(
        """
        INSERT INTO catalog.organisation_members (organisation_id, user_id, role, joined_at)
        VALUES
            ($1, $2, 'owner'::organisation_role,   $3),
            ($4, $5, 'manager'::organisation_role, $6)
        """,
        org_id,
        user_admin,
        now,
        org_id,
        user_alice,
        now,
    )

    # ── Venues ────────────────────────────────────────────────────────────────
    print("  Creating venues…")

    await conn.executemany(
        """
        INSERT INTO catalog.venues
            (id, name, address_line, city, country, latitude, longitude,
             geofence_radius_m, timezone, created_at, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """,
        [
            (
                venue_mad,
                "WiZink Center",
                "Av. de Felipe II, s/n",
                "Madrid",
                "ES",
                40.437775,
                -3.661543,
                200,
                "Europe/Madrid",
                now,
                now,
            ),
            (
                venue_bcn,
                "Palau Sant Jordi",
                "Passeig Olímpic, 5-7",
                "Barcelona",
                "ES",
                41.364667,
                2.153028,
                200,
                "Europe/Madrid",
                now,
                now,
            ),
        ],
    )

    # ── Events ────────────────────────────────────────────────────────────────
    print("  Creating events…")

    market_starts_at = now + timedelta(days=30)
    market_sale_ends_at = now - timedelta(days=1)

    event_rows = [
        (
            event_past,
            org_id,
            venue_mad,
            "Midnight Festival 2025",
            "An unforgettable night of electronic music at WiZink Center.",
            datetime(2025, 12, 20, 22, 0, tzinfo=UTC),
            datetime(2025, 12, 21, 6, 0, tzinfo=UTC),
            datetime(2025, 11, 1, 10, 0, tzinfo=UTC),
            datetime(2025, 12, 19, 23, 59, tzinfo=UTC),
            4,
            "Madrid",
        ),
        (
            event_now,
            org_id,
            venue_bcn,
            "Summer Beats 2026",
            "The biggest summer festival hits Barcelona's iconic Palau Sant Jordi.",
            datetime(2026, 8, 15, 20, 0, tzinfo=UTC),
            datetime(2026, 8, 16, 2, 0, tzinfo=UTC),
            datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
            datetime(2026, 8, 14, 23, 59, tzinfo=UTC),
            4,
            "Barcelona",
        ),
        (
            event_future,
            org_id,
            venue_mad,
            "Techno Underground 2026",
            "Halloween night goes underground. Limited capacity, maximum vibes.",
            datetime(2026, 10, 31, 23, 0, tzinfo=UTC),
            datetime(2026, 11, 1, 7, 0, tzinfo=UTC),
            datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            datetime(2026, 10, 30, 23, 59, tzinfo=UTC),
            4,
            "Madrid",
        ),
        # Market test event: sale already ended, starts 30 days from now
        (
            event_market,
            org_id,
            venue_mad,
            "Neon Rave 2026",
            "A sold-out underground rave. Secondary market only.",
            market_starts_at,
            market_starts_at + timedelta(hours=8),
            now - timedelta(days=30),
            market_sale_ends_at,
            4,
            "Madrid",
        ),
    ]

    for row in event_rows:
        await conn.execute(
            """
            INSERT INTO catalog.events (
                id, organisation_id, venue_id, name, description,
                starts_at, ends_at, sale_starts_at, sale_ends_at,
                max_tickets_per_user, status,
                organiser_name, venue_city,
                queue_required, queue_admit_rate_per_minute,
                created_at, updated_at, published_at
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                'published'::text, $11,$12,
                false, 60,
                $13,$14,$15
            )
            """,
            row[0],
            row[1],
            row[2],  # id, org, venue
            row[3],
            row[4],  # name, description
            row[5],
            row[6],  # starts_at, ends_at
            row[7],
            row[8],  # sale_starts_at, sale_ends_at
            row[9],  # max_tickets_per_user
            "Qrew Events",
            row[10],  # organiser_name, venue_city
            now,
            now,
            now,  # created, updated, published
        )

    # ── Ticket types ──────────────────────────────────────────────────────────
    print("  Creating ticket types…")

    ticket_types = [
        # Past event
        (
            tt_past_ga,
            event_past,
            "General Admission",
            "Standard entry",
            500,
            100,
            3500,
            "EUR",
            0,
        ),
        (tt_past_vip, event_past, "VIP", "VIP lounge", 100, 20, 7500, "EUR", 1),
        # Current sale
        (
            tt_now_ga,
            event_now,
            "General Admission",
            "Standard entry",
            1000,
            3,
            2500,
            "EUR",
            0,
        ),
        (tt_now_vip, event_now, "VIP", "VIP area", 200, 1, 6500, "EUR", 1),
        (
            tt_now_artist,
            event_now,
            "Artist Meet",
            "Meet & greet pass",
            50,
            0,
            12000,
            "EUR",
            2,
        ),
        # Future sale
        (
            tt_fut_early,
            event_future,
            "Early Bird",
            "Limited early access",
            200,
            0,
            2000,
            "EUR",
            0,
        ),
        (
            tt_fut_ga,
            event_future,
            "General Admission",
            "Standard entry",
            800,
            0,
            3000,
            "EUR",
            1,
        ),
        # Market test
        (tt_market_ga, event_market, "General Admission", "Standard entry", 200, 200, 4500, "EUR", 0),
    ]

    await conn.executemany(
        """
        INSERT INTO catalog.ticket_types
            (id, event_id, name, description, capacity, reserved_count,
             price_cents, currency, position, created_at, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """,
        [
            (t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], now, now)
            for t in ticket_types
        ],
    )

    # ── Sales projections ─────────────────────────────────────────────────────
    print("  Creating sales projections…")

    # EventContext — mirrors catalog.events sale/capacity settings
    # Requires migration 0005 (adds starts_at column)
    await conn.executemany(
        """
        INSERT INTO sales.event_context
            (event_id, status, sale_starts_at, sale_ends_at, starts_at,
             max_tickets_per_user, queue_required, queue_admit_rate_per_minute, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        [
            (
                event_past,
                "published",
                datetime(2025, 11, 1, 10, 0, tzinfo=UTC),
                datetime(2025, 12, 19, 23, 59, tzinfo=UTC),
                datetime(2025, 12, 20, 22, 0, tzinfo=UTC),
                4,
                False,
                60,
                now,
            ),
            (
                event_now,
                "published",
                datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
                datetime(2026, 8, 14, 23, 59, tzinfo=UTC),
                datetime(2026, 8, 15, 20, 0, tzinfo=UTC),
                4,
                False,
                60,
                now,
            ),
            (
                event_future,
                "published",
                datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
                datetime(2026, 10, 30, 23, 59, tzinfo=UTC),
                datetime(2026, 10, 31, 23, 0, tzinfo=UTC),
                4,
                False,
                60,
                now,
            ),
            (
                event_market,
                "published",
                now - timedelta(days=30),
                market_sale_ends_at,
                market_starts_at,
                4,
                False,
                60,
                now,
            ),
        ],
    )

    # TicketTypeInventory — mirrors catalog.ticket_types capacity/price
    await conn.executemany(
        """
        INSERT INTO sales.ticket_type_inventory
            (ticket_type_id, event_id, capacity, reserved_count,
             price_cents, currency, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        [
            (tt_past_ga, event_past, 500, 100, 3500, "EUR", now),
            (tt_past_vip, event_past, 100, 20, 7500, "EUR", now),
            (tt_now_ga, event_now, 1000, 3, 2500, "EUR", now),
            (tt_now_vip, event_now, 200, 1, 6500, "EUR", now),
            (tt_now_artist, event_now, 50, 0, 12000, "EUR", now),
            (tt_fut_early, event_future, 200, 0, 2000, "EUR", now),
            (tt_fut_ga, event_future, 800, 0, 3000, "EUR", now),
            (tt_market_ga, event_market, 200, 200, 4500, "EUR", now),
        ],
    )

    # UserAgeContext — one row per user for fraud detection
    await conn.executemany(
        """
        INSERT INTO sales.user_age_context (user_id, registered_at, updated_at)
        VALUES ($1,$2,$3)
        """,
        [(uid, now, now) for uid in (user_alice, user_bob, user_admin)],
    )

    # ── Ticketing projections ─────────────────────────────────────────────────
    print("  Creating ticketing projections…")

    await conn.executemany(
        """
        INSERT INTO ticketing.event_venue_context
            (event_id, venue_id, event_status,
             latitude, longitude, geofence_radius_m, timezone, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        """,
        [
            (
                event_past,
                venue_mad,
                "published",
                40.437775,
                -3.661543,
                200,
                "Europe/Madrid",
                now,
            ),
            (
                event_now,
                venue_bcn,
                "published",
                41.364667,
                2.153028,
                200,
                "Europe/Madrid",
                now,
            ),
            (
                event_future,
                venue_mad,
                "published",
                40.437775,
                -3.661543,
                200,
                "Europe/Madrid",
                now,
            ),
            (
                event_market,
                venue_mad,
                "published",
                40.437775,
                -3.661543,
                200,
                "Europe/Madrid",
                now,
            ),
        ],
    )

    # ── Reservations ──────────────────────────────────────────────────────────
    print("  Creating reservations…")

    far_future = now + timedelta(days=365 * 5)

    await conn.executemany(
        """
        INSERT INTO sales.reservations
            (id, user_id, event_id, ticket_type_id, quantity, status, expires_at,
             created_at, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        [
            # alice — 1 GA at past event (paid)
            (
                res_alice_past,
                user_alice,
                event_past,
                tt_past_ga,
                1,
                "paid",
                far_future,
                now,
                now,
            ),
            # alice — 2 GA at Summer Beats (paid)
            (
                res_alice_now,
                user_alice,
                event_now,
                tt_now_ga,
                2,
                "paid",
                far_future,
                now,
                now,
            ),
            # bob — 1 GA at Summer Beats (pending payment)
            (
                res_bob_now,
                user_bob,
                event_now,
                tt_now_ga,
                1,
                "reserved",
                far_future,
                now,
                now,
            ),
            # admin — 1 GA at Neon Rave (paid, issued — for testing Sale button)
            (
                res_admin_market,
                user_admin,
                event_market,
                tt_market_ga,
                1,
                "paid",
                far_future,
                now,
                now,
            ),
            # alice — 1 GA at Neon Rave (paid, will be frozen for resale listing)
            (
                res_alice_market,
                user_alice,
                event_market,
                tt_market_ga,
                1,
                "paid",
                far_future,
                now,
                now,
            ),
        ],
    )

    # ── Tickets ───────────────────────────────────────────────────────────────
    print("  Creating tickets…")

    await conn.executemany(
        """
        INSERT INTO ticketing.tickets
            (id, reservation_id, event_id, ticket_type_id, owner_user_id, state,
             state_updated_at, issued_at, expired_at, holder_name, holder_dni,
             created_at, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        """,
        [
            # alice's past-event ticket — used
            (
                tk_alice_past,
                res_alice_past,
                event_past,
                tt_past_ga,
                user_alice,
                "used",
                now,
                now,
                None,
                "Alice Dev",
                None,
                now,
                now,
            ),
            # alice's Summer Beats tickets — issued
            (
                tk_alice_now1,
                res_alice_now,
                event_now,
                tt_now_ga,
                user_alice,
                "issued",
                now,
                now,
                None,
                "Alice Dev",
                None,
                now,
                now,
            ),
            (
                tk_alice_now2,
                res_alice_now,
                event_now,
                tt_now_ga,
                user_alice,
                "issued",
                now,
                now,
                None,
                "Alice Dev",
                None,
                now,
                now,
            ),
            # bob's pending ticket — reserved
            (
                tk_bob_now,
                res_bob_now,
                event_now,
                tt_now_ga,
                user_bob,
                "reserved",
                now,
                None,
                None,
                None,
                None,
                now,
                now,
            ),
            # admin's market ticket — issued (to test Sale button)
            (
                tk_admin_market,
                res_admin_market,
                event_market,
                tt_market_ga,
                user_admin,
                "issued",
                now,
                now,
                None,
                "Admin User",
                None,
                now,
                now,
            ),
            # alice's market ticket — frozen (listed on resale)
            (
                tk_alice_market,
                res_alice_market,
                event_market,
                tt_market_ga,
                user_alice,
                "frozen",
                now,
                now,
                None,
                "Alice Dev",
                None,
                now,
                now,
            ),
        ],
    )

    # ── Market test data ──────────────────────────────────────────────────────
    print("  Creating market test data…")

    # Alice's frozen ticket listed on the market
    await conn.execute(
        """
        INSERT INTO sales.market_listings
            (id, ticket_id, event_id, seller_user_id, ticket_type_id,
             price_cents, currency, state, listed_at, expires_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
        market_listing_id,
        tk_alice_market,
        event_market,
        user_alice,
        tt_market_ga,
        4500,
        "EUR",
        "assigned",  # already assigned to admin
        now,
        now + timedelta(days=30),
    )

    # Pending assignment for admin (buyer)
    await conn.execute(
        """
        INSERT INTO sales.market_assignments
            (id, listing_id, event_id, buyer_user_id, assigned_at, expires_at, state)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        market_assignment_id,
        market_listing_id,
        event_market,
        user_admin,
        now,
        now + timedelta(minutes=30),
        "pending",
    )

    # ── Passkeys (dummy dev credentials so login skips the setup flow) ────────
    print("  Creating dummy passkeys…")

    await conn.executemany(
        """
        INSERT INTO identity.passkey_credentials
            (id, user_id, credential_id, public_key, sign_count, aaguid, name, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        [
            (
                uuid.uuid4(),
                user_alice,
                b"dev-credential-alice",
                b"dev-public-key-alice",
                0,
                "00000000-0000-0000-0000-000000000000",
                "Dev Passkey",
                now,
            ),
            (
                uuid.uuid4(),
                user_admin,
                b"dev-credential-admin",
                b"dev-public-key-admin",
                0,
                "00000000-0000-0000-0000-000000000000",
                "Dev Passkey",
                now,
            ),
        ],
    )

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print("Database seeded successfully!")
    print()
    print("Users (password: Password123! / AdminPass1!):")
    print("  alice@qrew.dev  — regular, KYC approved, manager of Qrew Events")
    print("  bob@qrew.dev    — regular, KYC pending")
    print("  admin@qrew.dev  — admin, owner of Qrew Events  [password: AdminPass1!]")
    print()
    print("Events:")
    print(
        "  Midnight Festival 2025   — past, WiZink Center Madrid   (alice has 1 used ticket)"
    )
    print(
        "  Summer Beats 2026        — upcoming, sale open now       (alice: 2 issued, bob: 1 reserved)"
    )
    print("  Techno Underground 2026  — upcoming, sale opens Sep 2026")
    print("  Neon Rave 2026           — sold-out, sale ended, starts in 30 days")
    print("                             admin: 1 issued ticket (test Sale button)")
    print("                             alice: 1 frozen ticket listed on market")
    print("                             admin: 1 pending market assignment")


if __name__ == "__main__":
    asyncio.run(seed())
