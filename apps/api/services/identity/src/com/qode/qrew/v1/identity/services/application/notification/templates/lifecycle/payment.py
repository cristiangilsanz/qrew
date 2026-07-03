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
