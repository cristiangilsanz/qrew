"""One payment per outcome the provider can report."""

from __future__ import annotations

from .catalog import GENERAL, VIP
from .models import Payment

PAYMENTS = (
    Payment(
        key="succeeded-admin",
        user="admin",
        reservation="paid-admin",
        assignment=None,
        amount_cents=GENERAL.price_cents * 2,
        status="succeeded",
        created_hours_ago=47.9,
    ),
    Payment(
        key="processing-admin",
        user="admin",
        reservation="pending-admin",
        assignment=None,
        amount_cents=VIP.price_cents,
        status="processing",
        created_hours_ago=0.05,
    ),
    Payment(
        key="failed-admin",
        user="admin",
        reservation="cancelled-admin",
        assignment=None,
        amount_cents=GENERAL.price_cents,
        status="failed",
        created_hours_ago=11.9,
    ),
    Payment(
        key="refunded-admin",
        user="admin",
        reservation="past-admin",
        assignment=None,
        amount_cents=GENERAL.price_cents * 2,
        status="refunded",
        created_hours_ago=24 * 4,
    ),
    Payment(
        key="action-admin",
        user="admin",
        reservation=None,
        assignment="claim-admin",
        amount_cents=VIP.price_cents,
        status="requires_action",
        created_hours_ago=0.04,
    ),
    Payment(
        key="succeeded-user-a",
        user="user-a",
        reservation="paid-user-a",
        assignment=None,
        amount_cents=GENERAL.price_cents,
        status="succeeded",
        created_hours_ago=29.9,
    ),
)
