def kyc_status_email(full_name: str, status: str, reason: str | None) -> str:
    first_name = full_name.split(maxsplit=1)[0]
    approved = status == "approved"
    heading = (
        "Your identity has been verified!"
        if approved
        else "KYC verification unsuccessful"
    )
    intro = (
        "Great news — your KYC document has been reviewed and approved. "
        "You now have full access to Qrew."
        if approved
        else "Unfortunately, we were unable to verify your identity document."
    )
    reason_block = (
        f"<p><strong>Reason:</strong> {reason}</p>" if reason and not approved else ""
    )
    next_steps = (
        "<p>You can now use all features of the platform.</p>"
        if approved
        else (
            "<p>Please re-submit a clear, valid national ID document "
            "to complete your verification.</p>"
        )
    )
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>{heading}</title>
    <style type="text/css">
      body {{ width: 100% !important; height: 100%; margin: 0; background-color: #F2F4F6; color: #51545E; }}
      body, td, th {{ font-family: "Nunito Sans", Helvetica, Arial, sans-serif; }}
      h1 {{ margin-top: 0; color: #333333; font-size: 22px; font-weight: bold; }}
      p {{ color: #51545E; font-size: 16px; line-height: 1.625; margin: 0.4em 0 1.1875em; }}
      .email-wrapper {{ width: 100%; margin: 0; padding: 0; background-color: #F2F4F6; }}
      .email-body_inner {{ width: 570px; margin: 0 auto; padding: 0; background-color: #FFFFFF; }}
      .email-footer {{ width: 570px; margin: 0 auto; padding: 0; text-align: center; }}
      .email-footer p {{ color: #A8AAAF; font-size: 13px; }}
      .content-cell {{ padding: 45px; }}
      @media only screen and (max-width: 600px) {{
        .email-body_inner, .email-footer {{ width: 100% !important; }}
      }}
    </style>
  </head>
  <body>
    <table class="email-wrapper" width="100%" cellpadding="0" cellspacing="0" role="presentation">
      <tr>
        <td align="center">
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
            <tr>
              <td style="padding: 25px 0; text-align: center;">
                <strong style="font-size: 20px; color: #333333;">Qrew</strong>
              </td>
            </tr>
            <tr>
              <td>
                <table class="email-body_inner" align="center" width="570" cellpadding="0" cellspacing="0" role="presentation">
                  <tr>
                    <td class="content-cell">
                      <h1>{heading}</h1>
                      <p>Hi {first_name},</p>
                      <p>{intro}</p>
                      {reason_block}
                      {next_steps}
                      <p>If you have questions, contact us at <a href="mailto:support@qrew.com">support@qrew.com</a>.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td>
                <table class="email-footer" align="center" width="570" cellpadding="0" cellspacing="0" role="presentation">
                  <tr>
                    <td class="content-cell" align="center">
                      <p>Qrew &mdash; All rights reserved.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
