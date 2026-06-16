from audit_publisher.publisher import publish_audit_event

AUDIT_EVENTS_SUBJECT = "audit.events.v1"

__all__ = ["AUDIT_EVENTS_SUBJECT", "publish_audit_event"]
