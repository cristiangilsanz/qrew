from com.qode.qrew.v1.identity.services.application.notification.templates._base import (
    _cta_button,
    _fallback_link,
    base_email,
)


def email_change_verify_email(
    full_name: str, link: str, expire_hours: int, logo_url: str | None = None
) -> str:
    first = full_name.split(maxsplit=1)[0]
    content = (
        f"                      <h1>Confirm your new email, {first}!</h1>\n"
        f"                      <p>You requested an email address change.</p>\n"
        f"                      <p>Please confirm your new email address by clicking the button below.</p>\n\n"
        f"{_cta_button(link, 'Confirm email address')}\n\n"
        f"                      <p>This link expires in <strong>{expire_hours} hours</strong>.</p>\n"
        f"                      <p>If you did not request this change, you can safely ignore this message.</p>\n\n"
        f"{_fallback_link(link)}"
    )
    return base_email(
        title="Confirm your new email address",
        preheader="Confirm your new Qrew email address.",
        logo_url=logo_url,
        content_html=content,
    )
