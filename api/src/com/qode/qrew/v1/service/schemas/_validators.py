import phonenumbers
import zxcvbn
from MailChecker import MailChecker  # type: ignore[import-untyped]

PASSWORD_SECURITY_MIN_SCORE = 3


def validate_phone_number(v: str) -> str:
    """Reject phone numbers that are not valid for their region."""
    try:
        parsed = phonenumbers.parse(v, None)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Invalid phone number") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Phone number is not valid for its region")
    return v


def validate_strong_password(v: str) -> str:
    """Reject weak passwords."""
    result = zxcvbn.zxcvbn(v)
    if result["score"] < PASSWORD_SECURITY_MIN_SCORE:
        feedback = result["feedback"]["warning"] or "Password is too weak"
        raise ValueError(feedback)
    return v


def validate_non_disposable_email(v: str) -> str:
    """Reject emails from known disposable providers."""
    if not MailChecker.is_valid(v):  # type: ignore[no-untyped-call]
        raise ValueError("Disposable email addresses are not allowed")
    return v.lower()
