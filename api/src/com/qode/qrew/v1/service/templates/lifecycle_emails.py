def payment_succeeded_email(*, full_name: str, event_name: str) -> str:
    """Render the payment-succeeded confirmation body."""
    return (
        f"<p>Hi {full_name},</p>"
        f"<p>Your payment for <b>{event_name}</b> succeeded. "
        "Your tickets are now issued and ready to display.</p>"
    )


def payment_failed_email(*, full_name: str, event_name: str, reason: str | None) -> str:
    detail = f" Reason: {reason}." if reason else ""
    return (
        f"<p>Hi {full_name},</p>"
        f"<p>Your payment for <b>{event_name}</b> did not complete.{detail} "
        "Please retry within your reservation window.</p>"
    )


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


def tickets_frozen_email(*, full_name: str, ticket_count: int) -> str:
    return (
        f"<p>Hi {full_name},</p>"
        f"<p>We have frozen {ticket_count} ticket(s) bound to a device you "
        "just revoked. Re-enrol a new device and use the restore endpoint to "
        "use them again.</p>"
    )


def ticket_restored_email(*, full_name: str) -> str:
    return (
        f"<p>Hi {full_name},</p>"
        "<p>Your ticket is restored and ready to display on your new device.</p>"
    )
