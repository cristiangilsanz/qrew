import re
import uuid
from datetime import UTC, datetime

ObjectKey = str

_ALLOWED_KINDS = frozenset({"kyc", "event_image", "scanner_photo"})
_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_TENANT_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}(?::[A-Za-z0-9._-]{1,64})?$")
_KEY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{0,31}(?::[A-Za-z0-9._-]{1,64})?"
    r"/[a-z][a-z0-9_]{0,31}/\d{4}/\d{2}/\d{2}/[a-f0-9]{32}$"
)


def is_known_kind(kind: str) -> bool:
    """Return whether the kind is on the allow-list."""
    return kind in _ALLOWED_KINDS


def build_key(*, tenant: str, kind: str, now: datetime | None = None) -> ObjectKey:
    """Build a date-partitioned object key for a new upload."""
    if not _TENANT_PATTERN.fullmatch(tenant):
        raise ValueError("invalid tenant")
    if not _KIND_PATTERN.fullmatch(kind):
        raise ValueError("invalid kind")
    stamp = now or datetime.now(UTC)
    return f"{tenant}/{kind}/{stamp:%Y/%m/%d}/{uuid.uuid4().hex}"


def is_valid_key(key: str) -> bool:
    """Verify that a string matches the documented object key format."""
    return bool(_KEY_PATTERN.fullmatch(key))


def kind_for(key: ObjectKey) -> str:
    """Extract the kind segment from an object key."""
    return key.split("/")[1]
