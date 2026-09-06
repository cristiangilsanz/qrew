# builds and validates the object keys stored uploads are addressed by
import re
import uuid
from datetime import UTC, datetime

ObjectKey = str

_ALLOWED_KINDS = frozenset({"kyc", "event_image", "scanner_photo"})
_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_TENANT_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}(?::[A-Za-z0-9_-]{1,64})?$")
_KEY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]{0,31}(?::[A-Za-z0-9_-]{1,64})?"
    r"/[a-z][a-z0-9_]{0,31}/\d{4}/\d{2}/\d{2}/[a-f0-9]{32}$"
)


# checks whether a storage kind is recognised
def is_known_kind(kind: str) -> bool:
    return kind in _ALLOWED_KINDS


# builds a new object key scoped to a tenant kind and date
def build_key(*, tenant: str, kind: str, now: datetime | None = None) -> ObjectKey:
    if not _TENANT_PATTERN.fullmatch(tenant):
        raise ValueError("Tenant rejected.")
    if not _KIND_PATTERN.fullmatch(kind):
        raise ValueError("Object kind rejected.")
    stamp = now or datetime.now(UTC)
    return f"{tenant}/{kind}/{stamp:%Y/%m/%d}/{uuid.uuid4().hex}"


# checks whether a key matches the expected object key shape
def is_valid_key(key: str) -> bool:
    return bool(_KEY_PATTERN.fullmatch(key))


# reads the storage kind embedded in an object key
def kind_for(key: ObjectKey) -> str:
    return key.split("/")[1]
