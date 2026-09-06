# signs and verifies the urls used to upload and download storage objects
import hashlib
import hmac
import time
from dataclasses import dataclass

from com.qode.qrew.v1.identity.services.application.storage.errors import (
    SignatureExpiredError,
    SignatureInvalidError,
)


@dataclass(frozen=True)
class SignedUrl:
    url: str
    key: str
    expires_at: int
    content_type: str | None


# computes the signature that binds a request to its key and expiry
def _digest(secret: str, method: str, key: str, content_type: str, expires_at: int) -> str:
    payload = f"{method}|{key}|{content_type}|{expires_at}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# signs a request and returns its expiry and signature
def sign(
    *,
    secret: str,
    method: str,
    key: str,
    content_type: str,
    ttl_seconds: int,
    now: int | None = None,
) -> tuple[int, str]:
    issued_at = now if now is not None else int(time.time())
    expires_at = issued_at + ttl_seconds
    signature = _digest(secret, method.upper(), key, content_type, expires_at)
    return expires_at, signature


# verifies a request's signature and rejects it once it has expired
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
    current = now if now is not None else int(time.time())
    if expires_at < current:
        raise SignatureExpiredError("Signed url expired.")
    expected = _digest(secret, method.upper(), key, content_type, expires_at)
    if not hmac.compare_digest(expected, signature):
        raise SignatureInvalidError("Signed url signature rejected.")
