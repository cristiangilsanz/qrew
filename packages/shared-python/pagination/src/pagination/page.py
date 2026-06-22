from pydantic import BaseModel, Field

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class Page[T](BaseModel):
    """A single page of results together with a token for the next page."""

    items: list[T]
    next_cursor: str | None = Field(
        default=None,
        description="Opaque token to fetch the next page; null on the last page.",
    )
