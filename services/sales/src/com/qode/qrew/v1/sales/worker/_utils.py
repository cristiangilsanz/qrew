"""Shared helpers for sales worker subscribers."""

import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def parse(raw: bytes) -> dict[str, Any] | None:
    try:
        data = json.loads(raw.decode())
        assert isinstance(data, dict)
        return data  # type: ignore[return-value]
    except Exception as exc:
        await logger.awarning("worker.parse_error", error=repr(exc))
        return None
