from com.qode.qrew.v1.identity.services.application.notification.templates._base import base_email


def email_change_alert_email(full_name: str, new_email: str, logo_url: str | None = None) -> str:
    first = full_name.split(maxsplit=1)[0]
    masked = new_email[:2] + "***@" + new_email.split("@", 1)[1]
    content = (
        f"                      <h1>Email change requested, {first}!</h1>\n"
        f"                      <p>A request was made to change your email address to <strong>{masked}</strong>.</p>\n"
        f""
    )
    return base_email(
        title="Email change requested",
        preheader="A request was made to change your Qrew email address.",
        logo_url=logo_url,
        content_html=content,
    )
