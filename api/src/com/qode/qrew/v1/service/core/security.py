import hashlib
import secrets
import string
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import structlog
from passlib.context import CryptContext

from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a hash."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a hash"""
    return _pwd_context.verify(plain, hashed)


async def is_password_pwned(password: str) -> bool:
    """Return True if a password appears in the HaveIBeenPwned breach database."""
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

    except Exception:
        await logger.awarning("hibp_check_skipped", reason="HIBP API unavailable")
        return False


def generate_token(length: int = 32) -> str:
    """Return an URL-safe token."""
    return secrets.token_urlsafe(length)


def generate_otp(length: int = 6) -> str:
    """Return an OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def email_verification_token_expiry() -> datetime:
    """Return the UTC datetime at which an email verification token expires."""
    return datetime.now(UTC) + timedelta(
        hours=settings.email_verification_token_expire_hours
    )


def phone_number_otp_expiry() -> datetime:
    """Return the UTC datetime at which a phone number OTP expires."""
    return datetime.now(UTC) + timedelta(
        minutes=settings.phone_number_otp_expire_minutes
    )


def create_access_token(subject: str) -> str:
    """Return a signed JWT access token for the given subject."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(subject: str) -> str:
    """Return a signed JWT refresh token for the given subject."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")
