# turns each service's fixtures into rows through its own writer

from __future__ import annotations

from . import catalog, entry, identity, payments, queues, sales, ticketing

WRITERS = (identity, catalog, sales, ticketing, payments, entry)

__all__ = [
    "WRITERS",
    "catalog",
    "entry",
    "identity",
    "payments",
    "queues",
    "sales",
    "ticketing",
]
