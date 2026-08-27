"""Deterministic identifiers, so reseeding always lands on the same rows."""

from __future__ import annotations

import uuid
from functools import cache

_NAMESPACE = uuid.UUID("9f1d1b52-3f4a-4e2a-8c9d-6f0f5a2c7b10")


@cache
def ident(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, ":".join(parts))
