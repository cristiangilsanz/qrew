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
