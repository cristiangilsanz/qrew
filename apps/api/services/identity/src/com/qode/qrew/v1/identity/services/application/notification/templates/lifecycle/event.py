def event_cancelled_email(*, full_name: str, event_name: str) -> str:
    return (
        f"<p>Hi {full_name},</p>"
        f"<p><b>{event_name}</b> has been cancelled by the organiser. "
        "If you held a ticket, it will be refunded automatically.</p>"
    )


def ticket_cancelled_email(*, full_name: str, event_name: str, reason: str) -> str:
    return (
        f"<p>Hi {full_name},</p>"
        f"<p>Your ticket for <b>{event_name}</b> was cancelled ({reason}). "
        "If you believe this is in error, contact support.</p>"
    )
