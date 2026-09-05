# holds each domain event until the drainer confirms the broker took it
from outbox import EventOutboxMixin

from com.qode.qrew.v1.catalog.core.database import Base


class EventOutbox(EventOutboxMixin, Base):
    __table_args__ = {"schema": "catalog"}
