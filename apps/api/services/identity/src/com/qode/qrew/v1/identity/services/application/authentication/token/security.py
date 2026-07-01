import hashlib
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from passlib.context import CryptContext

from com.qode.qrew.v1.identity.core.utils import jwt as jwt_keys
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return _pwd_context.hash(password)  # type: ignore[no-any-return]


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hash."""
    return _pwd_context.verify(plain, hashed)  # type: ignore[no-any-return]


async def is_password_pwned(password: str) -> bool:
    """Check whether a password appears in known breach data."""
    if not settings.hibp_enabled:
        return False

    sha1 = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"Add-Padding": "true"},
            )
            response.raise_for_status()
            lines = response.text.splitlines()

        return any(line.split(":")[0] == suffix for line in lines)

    except Exception as exc:
        await logger.awarning("hibp_check_skipped", reason="HIBP API unavailable", error=repr(exc))
        return False


def generate_token(length: int = 32) -> str:
    """Generate a random url-safe token."""
    return secrets.token_urlsafe(length)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric one-time password."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def email_verification_token_expiry() -> datetime:
    """Return the expiry time for a new email verification token."""
    return datetime.now(UTC) + timedelta(hours=settings.email_verification_token_expire_hours)


def phone_number_otp_expiry() -> datetime:
    """Return the expiry time for a new phone one-time password."""
    return datetime.now(UTC) + timedelta(minutes=settings.phone_number_otp_expire_minutes)


def create_access_token(
    subject: str,
    device_id: str | None = None,
    session_jti: str | None = None,
) -> str:
    """Mint a signed access token."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if device_id is not None:
        payload["device_id"] = device_id
    if session_jti is not None:
        payload["jti"] = session_jti
    return jwt_keys.sign(jwt_keys.ACCESS, payload)


def create_setup_token(subject: str) -> str:
    """Mint a short-lived token for the onboarding flow."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "setup",
        "iat": now,
        "exp": now + timedelta(minutes=settings.setup_token_expire_minutes),
    }
    return jwt_keys.sign(jwt_keys.SETUP, payload)


def create_recovery_token(subject: str) -> str:
    """Mint a short-lived token for the account recovery flow."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "recovery",
        "iat": now,
        "exp": now + timedelta(minutes=settings.setup_token_expire_minutes),
    }
    return jwt_keys.sign(jwt_keys.RECOVERY, payload)


def create_refresh_token(subject: str) -> str:
    """Mint a signed refresh token."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt_keys.sign(jwt_keys.REFRESH, payload)


def decode_refresh_token(token: str) -> dict[str, object]:
    """Decode and validate a refresh token."""
    return jwt_keys.verify(jwt_keys.REFRESH, token)


def extract_jti(token: str) -> str | None:
    """Extract the token identifier claim from a refresh token."""
    payload = jwt_keys.verify(jwt_keys.REFRESH, token)
    jti = payload.get("jti")
    return jti if isinstance(jti, str) else None
