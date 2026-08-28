# renders the html body of the account verification email
from com.qode.qrew.v1.identity.services.application.notification.templates._base import (
    cta_button,
    fallback_link,
    base_email,
)


# renders the email body carrying the account verification link
def verification_link_email(
    full_name: str, link: str, expire_hours: int, logo_url: str | None = None
) -> str:
    first = full_name.split(maxsplit=1)[0]
    content = (
        f"                      <h1>Verify your email, {first}!</h1>\n"
        f"                      <p>Thanks for signing up.</p>\n"
        f"                      <p>Please confirm your email address by clicking the button below.</p>\n\n"
        f"{cta_button(link, 'Verify email address')}\n\n"
        f"                      <p>This link expires in <strong>{expire_hours} hours</strong>.</p>\n"
        f"                      <p>If you did not create an account, you can safely ignore this message.</p>\n\n"
        f"{fallback_link(link)}"
    )
    return base_email(
        title="Verify your Qrew account",
        preheader="Verify your email address to get started with Qrew.",
        logo_url=logo_url,
        content_html=content,
    )
