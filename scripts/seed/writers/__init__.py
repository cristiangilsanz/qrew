"""Every writer takes the same arguments and owns exactly one schema."""

from __future__ import annotations

from . import catalog, entry, identity, payments, sales, ticketing

WRITERS = (identity, catalog, sales, ticketing, payments, entry)

__all__ = ["WRITERS", "catalog", "entry", "identity", "payments", "sales", "ticketing"]
