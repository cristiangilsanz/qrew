import hmac


def matches_internal_key(provided: str, expected: str) -> bool:
    """Compares an internal key in constant time, rejecting an unset expectation."""
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)
