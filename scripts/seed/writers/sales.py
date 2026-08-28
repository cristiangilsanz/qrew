# writes the fixture reservations listings assignments and queue entries into sales

from __future__ import annotations

import asyncpg

from ..core import SeedConfig, Timeline, hash_pii, ident
from ..data import Dataset

NAME = "sales"


# inserts every sales fixture row
async def write(
    conn: asyncpg.Connection, data: Dataset, when: Timeline, cfg: SeedConfig
) -> None:
    for event in data.events:
        await conn.execute(
            """
            INSERT INTO sales.event_context (
                event_id, status, starts_at, sale_starts_at, sale_ends_at,
                max_tickets_per_user, queue_required, queue_admit_rate_per_minute,
                updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            event.id,
            event.status,
            event.starts_at(when),
            event.sale_starts_at(when),
            event.sale_ends_at(when),
            event.max_per_user,
            event.queue_required,
            event.queue_rate,
            when.now,
        )
        for tier in event.ticket_types:
            await conn.execute(
                """
                INSERT INTO sales.ticket_type_inventory (
                    ticket_type_id, event_id, capacity, reserved_count, price_cents,
                    currency, updated_at
                ) VALUES ($1, $2, $3, $4, $5, 'EUR', $6)
                """,
                tier.id(event.key),
                event.id,
                tier.capacity,
                tier.reserved,
                tier.price_cents,
                when.now,
            )

    for person in data.people:
        await conn.execute(
            """
            INSERT INTO sales.user_age_context (
                user_id, registered_at, phone_e164, updated_at
            )
            VALUES ($1, $2, $3, $4)
            """,
            person.id,
            when.days(-30),
            person.phone,
            when.now,
        )

    await conn.execute(
        """
        INSERT INTO sales.fingerprint_context (fingerprint_hash, distinct_user_count,
                                               last_seen_at, updated_at)
        VALUES ($1, 3, $2, $2)
        """,
        hash_pii("shared-device-fingerprint"),
        when.hours(-4),
    )

    for reservation in data.reservations:
        event = data.event(reservation.event)
        tier = data.ticket_type(reservation.event, reservation.ticket_type)
        await conn.execute(
            """
            INSERT INTO sales.reservations (
                id, user_id, event_id, ticket_type_id, quantity, status, expires_at,
                requires_review, risk_score, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10)
            """,
            reservation.id,
            data.person(reservation.user).id,
            event.id,
            tier.id(event.key),
            reservation.quantity,
            reservation.status,
            when.minutes(reservation.expires_in_minutes),
            reservation.requires_review,
            reservation.risk_score,
            when.hours(-reservation.created_hours_ago),
        )
        for position, (holder_name, holder_dni) in enumerate(
            reservation.holders, start=1
        ):
            await conn.execute(
                """
                INSERT INTO sales.reservation_holders (id, reservation_id, position,
                                                       holder_name, holder_dni)
                VALUES ($1, $2, $3, $4, $5)
                """,
                ident("holder", reservation.key, str(position)),
                reservation.id,
                position,
                holder_name,
                holder_dni,
            )

    for listing in data.listings:
        await conn.execute(
            """
            INSERT INTO sales.market_listings (
                id, ticket_id, event_id, seller_user_id, ticket_type_id, price_cents,
                currency, state, listed_at, expires_at, completed_at, cancelled_at
            ) VALUES ($1, $2, $3, $4, $5, $6, 'EUR', $7, $8, $9, $10, $11)
            """,
            listing.id,
            data.ticket(listing.ticket).id,
            data.event(listing.event).id,
            data.person(listing.seller).id,
            data.ticket_type(listing.event, listing.ticket_type).id(listing.event),
            listing.price_cents,
            listing.state,
            when.hours(-listing.listed_hours_ago),
            when.hours(listing.expires_in_hours),
            when.hours(-1) if listing.completed else None,
            when.hours(-1) if listing.cancelled else None,
        )

    for assignment in data.assignments:
        await conn.execute(
            """
            INSERT INTO sales.market_assignments (
                id, listing_id, event_id, buyer_user_id, assigned_at, expires_at,
                paid_at,
                payment_intent_id, holder_name, holder_dni, state
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            assignment.id,
            data.listing(assignment.listing).id,
            data.event(assignment.event).id,
            data.person(assignment.buyer).id,
            when.minutes(-assignment.assigned_minutes_ago),
            when.minutes(assignment.expires_in_minutes),
            when.minutes(-assignment.assigned_minutes_ago + 1)
            if assignment.paid
            else None,
            f"pi_seed_{assignment.key}" if assignment.paid else None,
            assignment.holder_name,
            assignment.holder_dni,
            assignment.state,
        )

    for position, (event_key, person_key, tiebreak) in enumerate(data.queue):
        await conn.execute(
            """
            INSERT INTO sales.market_queue_entries (
                id, event_id, user_id, tiebreak, joined_at
            )
            VALUES ($1, $2, $3, $4, $5)
            """,
            ident("queue", event_key, person_key),
            data.event(event_key).id,
            data.person(person_key).id,
            tiebreak,
            when.minutes(-30 + position),
        )
