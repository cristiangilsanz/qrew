def verification_link_email(full_name: str, link: str, expire_hours: int) -> str:
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="x-apple-disable-message-reformatting" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="color-scheme" content="light dark" />
    <meta name="supported-color-schemes" content="light dark" />
    <title>Verify your Qrew account</title>
    <style type="text/css" rel="stylesheet" media="all">
      @import url("https://fonts.googleapis.com/css?family=Nunito+Sans:400,700&display=swap");

      body {{
        width: 100% !important;
        height: 100%;
        margin: 0;
        -webkit-text-size-adjust: none;
        background-color: #F2F4F6;
        color: #51545E;
      }}

      a {{ color: #3869D4; }}
      a img {{ border: none; }}
      td {{ word-break: break-word; }}

      .preheader {{
        display: none !important;
        visibility: hidden;
        mso-hide: all;
        font-size: 1px;
        line-height: 1px;
        max-height: 0;
        max-width: 0;
        opacity: 0;
        overflow: hidden;
      }}

      body, td, th {{
        font-family: "Nunito Sans", Helvetica, Arial, sans-serif;
      }}

      h1 {{
        margin-top: 0;
        color: #333333;
        font-size: 22px;
        font-weight: bold;
        text-align: left;
      }}

      p {{
        color: #51545E;
        font-size: 16px;
        line-height: 1.625;
        margin: 0.4em 0 1.1875em;
      }}

      p.sub {{ font-size: 13px; }}

      .email-wrapper {{
        width: 100%;
        margin: 0;
        padding: 0;
        background-color: #F2F4F6;
      }}

      .email-content {{ width: 100%; margin: 0; padding: 0; }}

      .email-masthead {{
        padding: 25px 0;
        text-align: center;
      }}

      .email-masthead_name {{
        font-size: 20px;
        font-weight: bold;
        color: #333333;
        text-decoration: none;
      }}

      .email-body {{ width: 100%; margin: 0; padding: 0; }}

      .email-body_inner {{
        width: 570px;
        margin: 0 auto;
        padding: 0;
        background-color: #FFFFFF;
      }}

      .email-footer {{
        width: 570px;
        margin: 0 auto;
        padding: 0;
        text-align: center;
      }}

      .email-footer p {{ color: #A8AAAF; }}

      .content-cell {{ padding: 45px; }}

      .button {{
        background-color: #3869D4;
        border-top: 10px solid #3869D4;
        border-right: 18px solid #3869D4;
        border-bottom: 10px solid #3869D4;
        border-left: 18px solid #3869D4;
        display: inline-block;
        color: #FFF !important;
        text-decoration: none;
        border-radius: 3px;
        box-shadow: 0 2px 3px rgba(0,0,0,0.16);
        -webkit-text-size-adjust: none;
        box-sizing: border-box;
        font-weight: bold;
        font-size: 15px;
      }}

      .body-action {{
        width: 100%;
        margin: 30px auto;
        padding: 0;
        text-align: center;
      }}

      .body-sub {{
        margin-top: 25px;
        padding-top: 25px;
        border-top: 1px solid #EAEAEC;
      }}

      @media only screen and (max-width: 600px) {{
        .email-body_inner, .email-footer {{ width: 100% !important; }}
        .button {{ width: 100% !important; text-align: center !important; }}
      }}

      @media (prefers-color-scheme: dark) {{
        body, .email-body, .email-body_inner, .email-content,
        .email-wrapper, .email-masthead, .email-footer {{
          background-color: #333333 !important;
          color: #FFF !important;
        }}
        p, h1, span {{ color: #FFF !important; }}
        .email-masthead_name {{ color: #FFF !important; }}
      }}

      :root {{
        color-scheme: light dark;
        supported-color-schemes: light dark;
      }}
    </style>
  </head>
  <body>
    <span class="preheader">Verify your email address to get started with Qrew.</span>
    <table class="email-wrapper" width="100%" cellpadding="0" cellspacing="0" role="presentation">
      <tr>
        <td align="center">
          <table class="email-content" width="100%" cellpadding="0" cellspacing="0" role="presentation">

            <!-- Masthead -->
            <tr>
              <td class="email-masthead">
                <a href="https://qrew.com" class="email-masthead_name">Qrew</a>
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td class="email-body" width="570" cellpadding="0" cellspacing="0">
                <table class="email-body_inner" align="center" width="570" cellpadding="0" cellspacing="0" role="presentation">
                  <tr>
                    <td class="content-cell">
                      <h1>Verify your email, {full_name.split(maxsplit=1)[0]}!</h1>
                      <p>Thanks for signing up.</p>
                      <p>Please confirm your email address by clicking the button below.</p>

                      <!-- CTA Button -->
                      <table class="body-action" align="center" width="100%" cellpadding="0" cellspacing="0" role="presentation">
                        <tr>
                          <td align="center">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
                              <tr>
                                <td align="center">
                                  <a href="{link}" class="button" target="_blank">Verify email address</a>
                                </td>
                              </tr>
                            </table>
                          </td>
                        </tr>
                      </table>

                      <p>This link expires in <strong>{expire_hours} hours</strong>. </p>
                      <p>If you did not create an account, you can safely ignore this message.</p>

                      <!-- Fallback link -->
                      <table class="body-sub" role="presentation">
                        <tr>
                          <td>
                            <p class="sub">If the button above doesn't work, copy and paste this URL into your browser:</p>
                            <p class="sub"><a href="{link}">{link}</a></p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td>
                <table class="email-footer" align="center" width="570" cellpadding="0" cellspacing="0" role="presentation">
                  <tr>
                    <td class="content-cell" align="center">
                      <p class="sub">Qrew &mdash; All rights reserved.</p>
                      <p class="sub">If you have questions, reply to this email or contact <a href="mailto:support@qrew.com">support@qrew.com</a>.</p>
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
