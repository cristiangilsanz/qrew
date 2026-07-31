from com.qode.qrew.v1.identity.services.application.notification.templates._base import (
    _cta_button,
    _fallback_link,
    base_email,
)


def forgot_password_email(
    full_name: str, link: str, expire_hours: int, logo_url: str | None = None
) -> str:
    first = full_name.split(maxsplit=1)[0]
    content = (
        f"                      <h1>Reset your password, {first}!</h1>\n"
        f"                      <p>You requested a password reset.</p>\n"
        f"                      <p>Click the button below to choose a new password.</p>\n\n"
        f"{_cta_button(link, 'Reset password')}\n\n"
        f"                      <p>This link expires in <strong>{expire_hours} hours</strong>.</p>\n"
        f"                      <p>If you did not request a password reset, you can safely ignore this message.</p>\n\n"
        f"{_fallback_link(link)}"
    )
    return base_email(
        title="Reset your Qrew password",
        preheader="Reset the password for your Qrew account.",
        logo_url=logo_url,
        content_html=content,
    )
