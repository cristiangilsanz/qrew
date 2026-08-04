#!/usr/bin/env python3
# ruff: noqa: E501

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


def _pg_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main() -> None:
    cfg = yaml.safe_load(IDENTITY_CFG.read_text())
    fernet = _make_fernet(
        cfg["pii_encryption_key"], cfg.get("pii_encryption_previous_keys", "")
    )
    db_url = _pg_url(cfg["database_url"])

    conn = await asyncpg.connect(db_url)
    now = datetime.now(UTC)

    def dt(delta: timedelta) -> datetime:
        return now + delta

    def u(hex_str: str) -> uuid.UUID:
        return uuid.UUID(hex_str)

    try:
        # Stable UUIDs so reseeding is idempotent
        u_admin = u("ffffffff-0001-0001-0001-000000000001")
        u_user1 = u("ffffffff-0002-0002-0002-000000000002")
        u_user2 = u("ffffffff-0003-0003-0003-000000000003")

        o_demo = u("00000001-0001-0001-0001-000000000001")

        v_alpha = u("00000010-0010-0010-0010-000000000010")
        v_beta = u("00000020-0020-0020-0020-000000000020")
        v_gamma = u("00000030-0030-0030-0030-000000000030")

        e_a = u("00000100-0100-0100-0100-000000000100")  # published, sale open
        e_b = u("00000200-0200-0200-0200-000000000200")  # published, sale pending
        e_c = u("00000300-0300-0300-0300-000000000300")  # ongoing
        e_d = u("00000400-0400-0400-0400-000000000400")  # draft
        e_e = u("00000500-0500-0500-0500-000000000500")  # cancelled
        e_f = u("00000600-0600-0600-0600-000000000600")  # published, sale ended
        e_g = u("00000700-0700-0700-0700-000000000700")  # published, past

        tt_a_ga = u("00001000-0001-0001-0001-000000000001")
        tt_a_vip = u("00001000-0002-0002-0002-000000000002")
        tt_b_eb = u("00002000-0001-0001-0001-000000000001")
        tt_b_ga = u("00002000-0002-0002-0002-000000000002")
        tt_c_ga = u("00003000-0001-0001-0001-000000000001")
        tt_c_vip = u("00003000-0002-0002-0002-000000000002")
        tt_d_ga = u("00004000-0001-0001-0001-000000000001")
        tt_e_ga = u("00005000-0001-0001-0001-000000000001")
        tt_f_ga = u("00006000-0001-0001-0001-000000000001")
        tt_g_ga = u("00007000-0001-0001-0001-000000000001")
        tt_g_vip = u("00007000-0002-0002-0002-000000000002")

        # Admin reservations
        r_a = u("00010000-0001-0001-0001-000000000001")  # paid
        r_b = u("00010000-0002-0002-0002-000000000002")  # reserved
        r_c = u("00010000-0003-0003-0003-000000000003")  # paid
        r_f = u("00010000-0004-0004-0004-000000000004")  # expired
        r_g = u("00010000-0005-0005-0005-000000000005")  # paid past

        # Admin tickets covering every TicketState
        t_issued = u("00100000-0001-0001-0001-000000000001")  # issued
        t_on_sale = u("00100000-0002-0002-0002-000000000002")  # on_sale
        t_reserved = u("00100000-0003-0003-0003-000000000003")  # reserved
        t_redeemed = u("00100000-0004-0004-0004-000000000004")  # redeemed
        t_scanning = u("00100000-0005-0005-0005-000000000005")  # scanning
        t_flagged = u("00100000-0006-0006-0006-000000000006")  # flagged
        t_expired = u("00100000-0007-0007-0007-000000000007")  # expired

        # Market
        ml_active = u("01000000-0001-0001-0001-000000000001")
        ml_completed = u("01000000-0002-0002-0002-000000000002")
        ma_pending = u("02000000-0001-0001-0001-000000000001")
        ma_paid = u("02000000-0002-0002-0002-000000000002")

        # Payments
        p_a = u("10000000-0001-0001-0001-000000000001")
        p_c = u("10000000-0002-0002-0002-000000000002")
        p_g = u("10000000-0003-0003-0003-000000000003")
        p_failed = u("10000000-0004-0004-0004-000000000004")
        p_market = u("10000000-0005-0005-0005-000000000005")

        # Scanner
        sc_alpha = u("20000000-0001-0001-0001-000000000001")

        print("Truncating tables...")
        await conn.execute("""
            TRUNCATE
                payments.payments,
                sales.market_assignments,
                sales.market_listings,
                sales.market_queue_entries,
                ticketing.tickets,
                sales.reservation_holders,
                sales.reservations,
                sales.event_context,
                sales.ticket_type_inventory,
                sales.user_age_context,
                sales.fingerprint_context,
                ticketing.event_venue_context,
                ticketing.device_context,
                entry.scans,
                entry.scanners,
                catalog.ticket_types,
                catalog.events,
                catalog.venues,
                catalog.organisation_members,
                catalog.organisations,
                identity.passkey_credentials,
                identity.users
            CASCADE
        """)

        print("Seeding users...")
        pw_regular = _hpw("Password123!")
        pw_admin = _hpw("AdminPass1!")

        users = [
            (
                u_admin,
                "Admin User",
                "admin@qrew.dev",
                "+34600000001",
                True,
                True,
                "approved",
                True,
                pw_admin,
            ),
            (
                u_user1,
                "User One",
                "user1@qrew.dev",
                "+34600000002",
                True,
                True,
                "approved",
                False,
                pw_regular,
            ),
            (
                u_user2,
                "User Two",
                "user2@qrew.dev",
                "+34600000003",
                True,
                True,
                "approved",
                False,
                pw_regular,
            ),
        ]

        for uid, name, email, phone, ev, pv, kyc, is_admin, pw in users:
            await conn.execute(
                """
                INSERT INTO identity.users (
                    id, full_name_ciphertext,
                    email_ciphertext, email_hash,
                    phone_number_ciphertext, phone_number_hash,
                    hashed_password, email_verified, phone_number_verified,
                    kyc_status, is_admin, is_active,
                    terms_accepted_at, registration_ip, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$15)
            """,
                uid,
                _enc(fernet, name),
                _enc(fernet, email),
                _hash(email),
                _enc(fernet, phone),
                _hash(phone),
                pw,
                ev,
                pv,
                kyc,
                is_admin,
                True,
                now,
                "127.0.0.1",
                now,
            )

        # Dummy passkeys satisfy the has_passkey check without being usable for auth
        print("Seeding passkeys...")
        for idx, uid in enumerate([u_admin, u_user1, u_user2]):
            await conn.execute(
                """
                INSERT INTO identity.passkey_credentials (
                    id, user_id, credential_id, public_key,
                    sign_count, aaguid, name, created_at
                ) VALUES ($1,$2,$3,$4,0,$5,'Seeded Device',$6)
            """,
                uuid.uuid4(),
                uid,
                bytes([idx + 1]) + b"\x00" * 31,
                b"\x04" + b"\x00" * 63,
                "00000000-0000-0000-0000-000000000000",
                now,
            )

        print("Seeding organisation...")
        await conn.execute(
            """
            INSERT INTO catalog.organisations (id, slug, name, description, created_at, updated_at)
            VALUES ($1, 'demo-org', 'Demo Organisation', $2, $3, $3)
        """,
            o_demo,
            "A demo organisation for testing all platform features.",
            now,
        )

        await conn.execute(
            """
            INSERT INTO catalog.organisation_members (organisation_id, user_id, role, joined_at)
            VALUES ($1, $2, 'owner', $3)
        """,
            o_demo,
            u_admin,
            now,
        )

        print("Seeding venues...")
        await conn.executemany(
            """
            INSERT INTO catalog.venues (
                id, name, address_line, city, country,
                latitude, longitude, geofence_radius_m,
                timezone, description, created_at, updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$11)
        """,
            [
                (
                    v_alpha,
                    "Venue Alpha",
                    "Calle Mayor 1",
                    "Madrid",
                    "ES",
                    40.416775,
                    -3.703790,
                    300,
                    "Europe/Madrid",
                    "Main venue for demo events.",
                    now,
                ),
                (
                    v_beta,
                    "Venue Beta",
                    "Passeig de Gracia 10",
                    "Barcelona",
                    "ES",
                    41.391648,
                    2.164994,
                    250,
                    "Europe/Madrid",
                    "Secondary venue for demo events.",
                    now,
                ),
                (
                    v_gamma,
                    "Venue Gamma",
                    "Calle Larios 5",
                    "Malaga",
                    "ES",
                    36.721395,
                    -4.421810,
                    150,
                    "Europe/Madrid",
                    "Third venue for demo events.",
                    now,
                ),
            ],
        )

        print("Seeding events...")
        events = [
            (
                e_a,
                v_alpha,
                "Event A",
                "Published event with sale open. Tickets are available now.",
                dt(timedelta(days=60)),
                dt(timedelta(days=60, hours=6)),
                dt(timedelta(days=-30)),
                dt(timedelta(days=59)),
                4,
                "published",
                "Madrid",
                False,
                dt(timedelta(days=-29)),
                None,
                None,
            ),
            (
                e_b,
                v_beta,
                "Event B",
                "Published event with sale not yet open. Queue required.",
                dt(timedelta(days=90)),
                dt(timedelta(days=90, hours=8)),
                dt(timedelta(days=30)),
                dt(timedelta(days=89)),
                6,
                "published",
                "Barcelona",
                True,
                dt(timedelta(days=-1)),
                None,
                None,
            ),
            (
                e_c,
                v_gamma,
                "Event C",
                "Ongoing event. Currently in progress.",
                dt(timedelta(hours=-2)),
                dt(timedelta(hours=4)),
                dt(timedelta(days=-45)),
                dt(timedelta(hours=-2)),
                4,
                "ongoing",
                "Malaga",
                False,
                dt(timedelta(days=-44)),
                dt(timedelta(hours=-2)),
                None,
            ),
            (
                e_d,
                v_alpha,
                "Event D",
                "Draft event. Not yet published.",
                dt(timedelta(days=120)),
                dt(timedelta(days=120, hours=8)),
                dt(timedelta(days=60)),
                dt(timedelta(days=119)),
                4,
                "draft",
                "Madrid",
                True,
                None,
                None,
                None,
            ),
            (
                e_e,
                v_beta,
                "Event E",
                "Cancelled event.",
                dt(timedelta(days=45)),
                dt(timedelta(days=45, hours=8)),
                dt(timedelta(days=-15)),
                dt(timedelta(days=44)),
                4,
                "cancelled",
                "Barcelona",
                False,
                dt(timedelta(days=-14)),
                None,
                dt(timedelta(days=-5)),
            ),
            (
                e_f,
                v_gamma,
                "Event F",
                "Published event. Sale has ended, doors open soon.",
                dt(timedelta(days=5)),
                dt(timedelta(days=5, hours=6)),
                dt(timedelta(days=-45)),
                dt(timedelta(days=-1)),
                2,
                "published",
                "Malaga",
                False,
                dt(timedelta(days=-44)),
                None,
                None,
            ),
            (
                e_g,
                v_alpha,
                "Event G",
                "Past published event. Ended 30 days ago.",
                dt(timedelta(days=-30)),
                dt(timedelta(days=-30, hours=6)),
                dt(timedelta(days=-90)),
                dt(timedelta(days=-31)),
                4,
                "published",
                "Madrid",
                False,
                dt(timedelta(days=-89)),
                None,
                None,
            ),
        ]

        for row in events:
            (
                eid,
                venue,
                name,
                desc,
                starts,
                ends,
                sale_s,
                sale_e,
                max_tix,
                status,
                city,
                queue,
                pub_at,
                start_at,
                cancel_at,
            ) = row
            await conn.execute(
                """
                INSERT INTO catalog.events (
                    id, organisation_id, venue_id, name, description, image_url,
                    starts_at, ends_at, sale_starts_at, sale_ends_at,
                    max_tickets_per_user, status, organiser_name, venue_city,
                    queue_required, queue_admit_rate_per_minute,
                    published_at, started_at, cancelled_at, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,NULL,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$19)
            """,
                eid,
                o_demo,
                venue,
                name,
                desc,
                starts,
                ends,
                sale_s,
                sale_e,
                max_tix,
                status,
                "Demo Organisation",
                city,
                queue,
                60,
                pub_at,
                start_at,
                cancel_at,
                now,
            )

        print("Seeding ticket types...")
        ticket_types = [
            (
                tt_a_ga,
                e_a,
                "General Admission",
                "Standing floor access.",
                500,
                200,
                7500,
                "EUR",
                0,
            ),
            (
                tt_a_vip,
                e_a,
                "VIP",
                "Front area with premium access.",
                50,
                10,
                18000,
                "EUR",
                1,
            ),
            (
                tt_b_eb,
                e_b,
                "Early Bird",
                "Limited early-bird price.",
                100,
                0,
                5500,
                "EUR",
                0,
            ),
            (
                tt_b_ga,
                e_b,
                "General Admission",
                "Standing floor access.",
                400,
                0,
                8500,
                "EUR",
                1,
            ),
            (
                tt_c_ga,
                e_c,
                "General Admission",
                "Full access to the venue floor.",
                1000,
                800,
                4500,
                "EUR",
                0,
            ),
            (
                tt_c_vip,
                e_c,
                "VIP",
                "Exclusive backstage access.",
                20,
                20,
                25000,
                "EUR",
                1,
            ),
            (
                tt_d_ga,
                e_d,
                "General Admission",
                "Standing floor access.",
                300,
                0,
                6500,
                "EUR",
                0,
            ),
            (
                tt_e_ga,
                e_e,
                "General Admission",
                "Event cancelled.",
                400,
                0,
                6000,
                "EUR",
                0,
            ),
            (
                tt_f_ga,
                e_f,
                "General Admission",
                "Sale is now closed.",
                300,
                150,
                5000,
                "EUR",
                0,
            ),
            (
                tt_g_ga,
                e_g,
                "General Admission",
                "Standing floor access.",
                200,
                200,
                3500,
                "EUR",
                0,
            ),
            (tt_g_vip, e_g, "VIP", "VIP lounge. Sold out.", 20, 20, 12000, "EUR", 1),
        ]

        for ttid, eid, name, desc, cap, res, price, curr, pos in ticket_types:
            await conn.execute(
                """
                INSERT INTO catalog.ticket_types (
                    id, event_id, name, description,
                    capacity, reserved_count, price_cents, currency,
                    position, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$10)
            """,
                ttid,
                eid,
                name,
                desc,
                cap,
                res,
                price,
                curr,
                pos,
                now,
            )

        print("Seeding reservations...")
        reservations = [
            (r_a, e_a, tt_a_ga, 2, "paid", dt(timedelta(hours=-23))),
            (r_b, e_b, tt_b_ga, 1, "reserved", dt(timedelta(minutes=15))),
            (r_c, e_c, tt_c_ga, 2, "paid", dt(timedelta(hours=-25))),
            (r_f, e_f, tt_f_ga, 1, "expired", dt(timedelta(days=-5))),
            (r_g, e_g, tt_g_ga, 1, "paid", dt(timedelta(days=-30, hours=-23))),
        ]

        for rid, eid, ttid, qty, status, expires in reservations:
            await conn.execute(
                """
                INSERT INTO sales.reservations (
                    id, user_id, event_id, ticket_type_id,
                    quantity, status, expires_at, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$8)
            """,
                rid,
                u_admin,
                eid,
                ttid,
                qty,
                status,
                expires,
                now,
            )

        print("Seeding reservation holders...")
        holders = [
            (r_a, 1, "Admin User", "12345678A"),
            (r_a, 2, "Guest One", "87654321B"),
            (r_b, 1, "Admin User", "12345678A"),
            (r_c, 1, "Admin User", "12345678A"),
            (r_c, 2, "Guest Two", "55443322C"),
            (r_f, 1, "Admin User", "12345678A"),
            (r_g, 1, "Admin User", "12345678A"),
        ]

        for rid, pos, name, dni in holders:
            await conn.execute(
                """
                INSERT INTO sales.reservation_holders (id, reservation_id, position, holder_name, holder_dni)
                VALUES ($1,$2,$3,$4,$5)
            """,
                uuid.uuid4(),
                rid,
                pos,
                name,
                dni,
            )

        print("Seeding tickets...")
        tickets = [
            (t_issued, r_a, e_a, tt_a_ga, "issued", now, "Admin User"),
            (t_on_sale, r_a, e_a, tt_a_ga, "on_sale", now, "Guest One"),
            (t_reserved, r_b, e_b, tt_b_ga, "reserved", None, "Admin User"),
            (
                t_redeemed,
                r_g,
                e_g,
                tt_g_ga,
                "redeemed",
                dt(timedelta(days=-30, hours=1)),
                "Admin User",
            ),
            (
                t_scanning,
                r_c,
                e_c,
                tt_c_ga,
                "scanning",
                dt(timedelta(hours=-1)),
                "Admin User",
            ),
            (
                t_flagged,
                r_c,
                e_c,
                tt_c_ga,
                "flagged",
                dt(timedelta(hours=-1)),
                "Guest Two",
            ),
            (t_expired, r_f, e_f, tt_f_ga, "expired", None, "Admin User"),
        ]

        for tid, rid, eid, ttid, state, issued, holder in tickets:
            await conn.execute(
                """
                INSERT INTO ticketing.tickets (
                    id, reservation_id, event_id, ticket_type_id, owner_user_id,
                    state, state_updated_at, issued_at,
                    holder_name, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$10)
            """,
                tid,
                rid,
                eid,
                ttid,
                u_admin,
                state,
                now,
                issued,
                holder,
                now,
            )

        print("Seeding market listings...")

        await conn.execute(
            """
            INSERT INTO sales.market_listings (
                id, ticket_id, event_id, seller_user_id, ticket_type_id,
                price_cents, currency, state, listed_at, expires_at
            ) VALUES ($1,$2,$3,$4,$5,$6,'EUR',$7,$8,$9)
        """,
            ml_active,
            t_on_sale,
            e_a,
            u_admin,
            tt_a_ga,
            1500,
            "assigned",
            now,
            dt(timedelta(hours=24)),
        )

        await conn.execute(
            """
            INSERT INTO sales.market_listings (
                id, ticket_id, event_id, seller_user_id, ticket_type_id,
                price_cents, currency, state, listed_at, expires_at, completed_at
            ) VALUES ($1,$2,$3,$4,$5,$6,'EUR',$7,$8,$9,$10)
        """,
            ml_completed,
            t_redeemed,
            e_g,
            u_admin,
            tt_g_ga,
            1200,
            "completed",
            dt(timedelta(days=-35)),
            dt(timedelta(days=-34)),
            dt(timedelta(days=-34)),
        )

        print("Seeding market assignments...")

        await conn.execute(
            """
            INSERT INTO sales.market_assignments (
                id, listing_id, event_id, buyer_user_id,
                assigned_at, expires_at, state, holder_name, holder_dni
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
            ma_pending,
            ml_active,
            e_a,
            u_admin,
            now,
            dt(timedelta(minutes=15)),
            "pending",
            "Admin User",
            "12345678A",
        )

        await conn.execute(
            """
            INSERT INTO sales.market_assignments (
                id, listing_id, event_id, buyer_user_id,
                assigned_at, expires_at, paid_at, state, holder_name, holder_dni
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
            ma_paid,
            ml_completed,
            e_g,
            u_admin,
            dt(timedelta(days=-34)),
            dt(timedelta(days=-34, hours=1)),
            dt(timedelta(days=-34)),
            "paid",
            "Admin User",
            "12345678A",
        )

        print("Seeding waitlist...")
        await conn.execute(
            """
            INSERT INTO sales.market_queue_entries (id, event_id, user_id, tiebreak, joined_at)
            VALUES ($1,$2,$3,$4,$5)
        """,
            uuid.uuid4(),
            e_b,
            u_admin,
            0,
            now,
        )

        print("Seeding payments...")
        payments = [
            (p_a, r_a, None, "pi_3QxAdmin001", 3000, "EUR", "succeeded", None, None),
            (p_c, r_c, None, "pi_3QxAdmin002", 2500, "EUR", "succeeded", None, None),
            (p_g, r_g, None, "pi_3QxAdmin003", 1200, "EUR", "succeeded", None, None),
            (
                p_failed,
                r_b,
                None,
                "pi_3QxAdmin004",
                3500,
                "EUR",
                "failed",
                "insufficient_funds",
                "Your card has insufficient funds.",
            ),
            (
                p_market,
                None,
                ma_pending,
                "pi_3QxAdmin005",
                1500,
                "EUR",
                "succeeded",
                None,
                None,
            ),
        ]

        for (
            pid,
            res_id,
            mkt_id,
            pi_id,
            amount,
            curr,
            status,
            fail_code,
            fail_msg,
        ) in payments:
            await conn.execute(
                """
                INSERT INTO payments.payments (
                    id, reservation_id, market_assignment_id, user_id,
                    provider, provider_payment_intent_id,
                    amount_cents, currency, status,
                    failure_code, failure_message, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,'stripe',$5,$6,$7,$8,$9,$10,$11,$11)
            """,
                pid,
                res_id,
                mkt_id,
                u_admin,
                pi_id,
                amount,
                curr,
                status,
                fail_code,
                fail_msg,
                now,
            )

        print("Seeding scanner...")
        await conn.execute(
            """
            INSERT INTO entry.scanners (id, name, venue_id, created_by, created_at, is_active)
            VALUES ($1, 'Main Gate Venue Alpha', $2, $3, $4, true)
        """,
            sc_alpha,
            v_alpha,
            u_admin,
            now,
        )

        print("Seeding projections...")

        event_ctx_rows = [
            (
                e_a,
                "published",
                dt(timedelta(days=-30)),
                dt(timedelta(days=59)),
                dt(timedelta(days=60)),
                4,
                False,
                60,
            ),
            (
                e_b,
                "published",
                dt(timedelta(days=30)),
                dt(timedelta(days=89)),
                dt(timedelta(days=90)),
                6,
                True,
                60,
            ),
            (
                e_c,
                "ongoing",
                dt(timedelta(days=-45)),
                dt(timedelta(hours=-2)),
                dt(timedelta(hours=-2)),
                4,
                False,
                60,
            ),
            (
                e_d,
                "draft",
                dt(timedelta(days=60)),
                dt(timedelta(days=119)),
                dt(timedelta(days=120)),
                4,
                True,
                60,
            ),
            (
                e_e,
                "cancelled",
                dt(timedelta(days=-15)),
                dt(timedelta(days=44)),
                dt(timedelta(days=45)),
                4,
                False,
                60,
            ),
            (
                e_f,
                "published",
                dt(timedelta(days=-45)),
                dt(timedelta(days=-1)),
                dt(timedelta(days=5)),
                2,
                False,
                60,
            ),
            (
                e_g,
                "published",
                dt(timedelta(days=-90)),
                dt(timedelta(days=-31)),
                dt(timedelta(days=-30)),
                4,
                False,
                60,
            ),
        ]

        for eid, status, sale_s, sale_e, starts, max_tix, queue, rate in event_ctx_rows:
            await conn.execute(
                """
                INSERT INTO sales.event_context (
                    event_id, status, sale_starts_at, sale_ends_at, starts_at,
                    max_tickets_per_user, queue_required, queue_admit_rate_per_minute, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """,
                eid,
                status,
                sale_s,
                sale_e,
                starts,
                max_tix,
                queue,
                rate,
                now,
            )

        for ttid, eid, _name, _desc, cap, res, price, curr, _pos in ticket_types:
            await conn.execute(
                """
                INSERT INTO sales.ticket_type_inventory (
                    ticket_type_id, event_id, capacity, reserved_count,
                    price_cents, currency, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
                ttid,
                eid,
                cap,
                res,
                price,
                curr,
                now,
            )

        for uid, _name, _email, phone, _ev, _pv, _kyc, _admin, _pw in users:
            await conn.execute(
                """
                INSERT INTO sales.user_age_context (user_id, registered_at, phone_e164, updated_at)
                VALUES ($1,$2,$3,$4)
            """,
                uid,
                now,
                phone,
                now,
            )

        venue_coords = {
            v_alpha: (40.416775, -3.703790, 300, "Europe/Madrid"),
            v_beta: (41.391648, 2.164994, 250, "Europe/Madrid"),
            v_gamma: (36.721395, -4.421810, 150, "Europe/Madrid"),
        }
        event_venue_map = [
            (
                e_a,
                v_alpha,
                dt(timedelta(days=60)),
                dt(timedelta(days=60, hours=6)),
                "published",
            ),
            (
                e_b,
                v_beta,
                dt(timedelta(days=90)),
                dt(timedelta(days=90, hours=8)),
                "published",
            ),
            (e_c, v_gamma, dt(timedelta(hours=-2)), dt(timedelta(hours=4)), "ongoing"),
            (
                e_d,
                v_alpha,
                dt(timedelta(days=120)),
                dt(timedelta(days=120, hours=8)),
                "draft",
            ),
            (
                e_e,
                v_beta,
                dt(timedelta(days=45)),
                dt(timedelta(days=45, hours=8)),
                "cancelled",
            ),
            (
                e_f,
                v_gamma,
                dt(timedelta(days=5)),
                dt(timedelta(days=5, hours=6)),
                "published",
            ),
            (
                e_g,
                v_alpha,
                dt(timedelta(days=-30)),
                dt(timedelta(days=-30, hours=6)),
                "published",
            ),
        ]

        for eid, vid, starts, ends, status in event_venue_map:
            lat, lon, radius, tz = venue_coords[vid]
            await conn.execute(
                """
                INSERT INTO ticketing.event_venue_context (
                    event_id, venue_id, event_status,
                    latitude, longitude, geofence_radius_m, timezone,
                    starts_at, ends_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
                eid,
                vid,
                status,
                lat,
                lon,
                radius,
                tz,
                starts,
                ends,
                now,
            )

        print()
        print("✓  Database seeded.")
        print()
        print(
            "  admin@qrew.dev  /  AdminPass1!   — org owner, all event states, all ticket states"
        )
        print("  user1@qrew.dev  /  Password123!  — empty")
        print("  user2@qrew.dev  /  Password123!  — empty")
        print()
        print("  Events: A published sale open · B published sale pending queue")
        print("          C ongoing · D draft · E cancelled · F sale ended · G past")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
