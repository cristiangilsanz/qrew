import hashlib
import hmac
import time
from dataclasses import dataclass

from com.qode.qrew.v1.identity.services.storage.errors import (
    SignatureExpiredError,
    SignatureInvalidError,
)


@dataclass(frozen=True)
class SignedUrl:
    url: str
    key: str
    expires_at: int
    content_type: str | None


def _digest(secret: str, method: str, key: str, content_type: str, expires_at: int) -> str:
    payload = f"{method}|{key}|{content_type}|{expires_at}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def sign(
    *,
    secret: str,
    method: str,
    key: str,
    content_type: str,
    ttl_seconds: int,
    now: int | None = None,
) -> tuple[int, str]:
    """Produce an expiry and HMAC for a signed URL."""
    issued_at = now if now is not None else int(time.time())
    expires_at = issued_at + ttl_seconds
    signature = _digest(secret, method.upper(), key, content_type, expires_at)
    return expires_at, signature


def verify(
    *,
    secret: str,
    method: str,
    key: str,
    content_type: str,
    expires_at: int,
    signature: str,
    now: int | None = None,
) -> None:
    """Validate the signature and expiry of a signed URL."""
    current = now if now is not None else int(time.time())
    if expires_at < current:
        raise SignatureExpiredError("signed url expired")
    expected = _digest(secret, method.upper(), key, content_type, expires_at)
    if not hmac.compare_digest(expected, signature):
        raise SignatureInvalidError("signed url signature mismatch")
