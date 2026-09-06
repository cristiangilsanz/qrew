# exposes the outbox event model and its dead letter query
from com.qode.qrew.v1.identity.models.outbox import OutboxEvent, dlq_query

__all__ = ["OutboxEvent", "dlq_query"]
