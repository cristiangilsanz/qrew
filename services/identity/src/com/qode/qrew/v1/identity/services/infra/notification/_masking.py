import re

_DIGIT_RE = re.compile(r"\D")


def mask_email(email: str) -> str:
    """Return a masked form of an email address."""
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def mask_phone_number(phone_number: str) -> str:
    """Return a masked form of a phone number."""
    digits = _DIGIT_RE.sub("", phone_number)
    return f"****{digits[-4:]}"
