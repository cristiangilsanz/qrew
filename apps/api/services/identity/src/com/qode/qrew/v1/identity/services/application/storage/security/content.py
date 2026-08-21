from typing import Final

_ALLOWED_MAGIC: Final[list[bytes]] = [
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"%PDF-",
]


def has_allowed_signature(content: bytes) -> bool:
    """Reports whether the payload starts with one of the accepted file signatures."""
    return any(content.startswith(magic) for magic in _ALLOWED_MAGIC)
