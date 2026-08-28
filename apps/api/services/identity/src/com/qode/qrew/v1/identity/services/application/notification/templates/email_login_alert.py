# renders the html body of the unusual sign in alert
from com.qode.qrew.v1.identity.services.application.notification.templates._base import base_email


# renders the email body alerting of an unusual sign in
def login_anomaly_alert_email(
    full_name: str,
    ip_address: str,
    location: str | None = None,
    logo_url: str | None = None,
) -> str:
    first = full_name.split(maxsplit=1)[0]
    location_display = location or "Unknown location"
    content = (
        f"                      <h1>Unusual sign-in detected, {first}!</h1>\n"
        f"                      <p>We detected an unusual sign-in on your account:</p>\n"
        f'                      <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin:16px 0;">\n'
        f'                        <tr><td style="background-color:#2a1a0a;border:1px solid #BF7318;border-radius:8px;padding:16px 18px;">\n'
        f'                          <table width="100%" cellpadding="0" cellspacing="0" role="presentation">\n'
        f"                            <tr>\n"
        f'                              <td width="44" valign="middle" style="font-size:28px;padding-right:14px;">&#128241;</td>\n'
        f'                              <td valign="middle">\n'
        f'                                <p style="margin:0 0 2px 0;color:#FFFFFF;font-size:15px;font-weight:bold;line-height:1.4;">{location_display}</p>\n'
        f'                                <p style="margin:0;color:#768293;font-size:13px;line-height:1.4;">{ip_address}</p>\n'
        f"                              </td>\n"
        f"                            </tr>\n"
        f"                          </table>\n"
        f"                        </td></tr>\n"
        f"                      </table>\n"
        f"                      <p>If that wasn't you, change your password and revoke sessions.</p>"
    )
    return base_email(
        title="Unusual sign-in to your Qrew account",
        preheader="We detected an unusual sign-in to your Qrew account.",
        logo_url=logo_url,
        content_html=content,
    )
