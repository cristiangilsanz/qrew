# defines the base error for domain failures in the sales service
class DomainError(Exception):
    # stores the error message and the field it refers to
    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
