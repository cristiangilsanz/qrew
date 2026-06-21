class DomainError(Exception):
    """Raised for any business-rule violation."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.message = message
        self.field = field
        super().__init__(message)


class EventNotFoundError(Exception):
    pass


class NotEventMemberError(Exception):
    pass
