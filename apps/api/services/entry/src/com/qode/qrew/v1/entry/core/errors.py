# defines the base errors for domain failures in the entry service
class DomainError(Exception):
    # stores the error message and the field it refers to
    def __init__(self, message: str, field: str | None = None) -> None:
        self.message = message
        self.field = field
        super().__init__(message)


class EventNotFoundError(Exception):
    pass


class NotEventMemberError(Exception):
    pass
