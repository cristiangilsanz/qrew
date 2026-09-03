# hashes passwords checks breaches and issues the tokens every auth flow needs
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

_pwd_context = CryptContext(schemes=["argon2"])


# hashes a password for storage
def hash_password(password: str) -> str:
    return _pwd_context.hash(password)  # type: ignore[no-any-return]


# checks a password against its stored hash
def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)  # type: ignore[no-any-return]


# checks a password against known breaches through have i been pwned
async def is_password_pwned(password: str) -> bool:
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


# generates a random url safe token
def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


# generates a random numeric one time code
def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


# computes when an email verification token expires
def email_verification_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=settings.email_verification_token_expire_hours)


# computes when a phone verification code expires
def phone_number_otp_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.phone_number_otp_expire_minutes)


# signs an access token for an authenticated user
def create_access_token(
    subject: str,
    device_id: str | None = None,
    session_jti: str | None = None,
    is_admin: bool = False,
    kyc_approved: bool = False,
    last_asserted_at: datetime | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if is_admin:
        payload["adm"] = True
    if kyc_approved:
        payload["kyc"] = True
    if device_id is not None:
        payload["device_id"] = device_id
    if session_jti is not None:
        payload["jti"] = session_jti
    # the gate reads this claim to tell how recently the holder proved presence
    if last_asserted_at is not None:
        stamped = last_asserted_at
        if stamped.tzinfo is None:
            stamped = stamped.replace(tzinfo=UTC)
        payload["last_asserted_at"] = int(stamped.timestamp())
    return jwt_keys.sign(jwt_keys.ACCESS, payload)


# signs a token for an account still completing setup
def create_setup_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "setup",
        "iat": now,
        "exp": now + timedelta(minutes=settings.setup_token_expire_minutes),
    }
    return jwt_keys.sign(jwt_keys.SETUP, payload)


# signs a token for an account undergoing recovery
def create_recovery_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "recovery",
        "iat": now,
        "exp": now + timedelta(minutes=settings.setup_token_expire_minutes),
    }
    return jwt_keys.sign(jwt_keys.RECOVERY, payload)


# signs a refresh token for a new session
def create_refresh_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt_keys.sign(jwt_keys.REFRESH, payload)


# verifies a refresh token and returns its claims
def decode_refresh_token(token: str) -> dict[str, object]:
    return jwt_keys.verify(jwt_keys.REFRESH, token)


# signs a token for a login pending two factor verification
def create_totp_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "type": "access",
        "scope": "totp",
        "iat": now,
        "exp": now + timedelta(minutes=settings.totp_token_expire_minutes),
    }
    return jwt_keys.sign(jwt_keys.TOTP, payload)


# reads the session identifier carried by a refresh token
def extract_jti(token: str) -> str | None:
    payload = jwt_keys.verify(jwt_keys.REFRESH, token)
    jti = payload.get("jti")
    return jti if isinstance(jti, str) else None
