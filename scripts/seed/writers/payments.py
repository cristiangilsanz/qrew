"""One payment per outcome the provider can report."""

from __future__ import annotations

import asyncpg

from ..core import SeedConfig, Timeline
from ..data import Dataset

NAME = "payments"


async def write(
    conn: asyncpg.Connection, data: Dataset, when: Timeline, cfg: SeedConfig
) -> None:
    for payment in data.payments:
        reservation = (
            next(r for r in data.reservations if r.key == payment.reservation).id
            if payment.reservation
            else None
        )
        assignment = (
            next(a for a in data.assignments if a.key == payment.assignment).id
            if payment.assignment
            else None
        )
        await conn.execute(
            """
            INSERT INTO payments.payments (
                id, reservation_id, market_assignment_id, user_id, provider,
                provider_payment_intent_id, amount_cents, currency, status,
                failure_code, failure_message, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, 'stripe', $5, $6, 'EUR', $7, $8, $9, $10, $10)
            """,
            payment.id,
            reservation,
            assignment,
            data.person(payment.user).id,
            f"pi_seed_{payment.key}",
            payment.amount_cents,
            payment.status,
            "card_declined" if payment.status == "failed" else None,
            "The card was declined." if payment.status == "failed" else None,
            when.hours(-payment.created_hours_ago),
        )
