# renders the html body of the kyc review outcome email
from com.qode.qrew.v1.identity.services.application.notification.templates._base import base_email


# renders the email body reporting the kyc review outcome
def kyc_status_email(
    full_name: str, status: str, reason: str | None, logo_url: str | None = None
) -> str:
    first = full_name.split(maxsplit=1)[0]
    approved = status == "approved"
    heading = (
        f"Your identity has been verified, {first}!"
        if approved
        else f"Your identity could not be verified, {first}."
    )
    intro = (
        "Great news! Your KYC document has been reviewed and approved."
        if approved
        else "Bad news! Your KYC document has been reviewed and could not be approved."
    )

    next_steps = (
        ""
        if approved
        else "                      <p>Please re-submit it to complete your verification.</p>\n"
    )
    content = (
        f"                      <h1>{heading}</h1>\n"
        f"                      <p>{intro}</p>\n"
        f"{next_steps}"
    )
    preheader = (
        "Your Qrew identity check has been approved."
        if approved
        else "Your Qrew identity check needs attention."
    )
    return base_email(
        title=heading,
        preheader=preheader,
        logo_url=logo_url,
        content_html=content,
    )
