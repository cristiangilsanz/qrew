# builds the html fragments shared by every email template
# builds the call to action button markup
def cta_button(url: str, label: str) -> str:
    return (
        f'      <table class="body-action" align="center" width="100%" cellpadding="0" cellspacing="0" role="presentation">\n'
        f"        <tr>\n"
        f'          <td align="center">\n'
        f'            <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">\n'
        f"              <tr>\n"
        f'                <td align="center">\n'
        f'                  <a href="{url}" class="button" target="_blank">{label}</a>\n'
        f"                </td>\n"
        f"              </tr>\n"
        f"            </table>\n"
        f"          </td>\n"
        f"        </tr>\n"
        f"      </table>"
    )


# builds the plain link shown when the button cannot be clicked
def fallback_link(url: str) -> str:
    return (
        f'      <table class="body-sub" role="presentation">\n'
        f"        <tr>\n"
        f"          <td>\n"
        f'            <p class="sub">If the button above doesn\'t work, copy and paste this URL into your browser:</p>\n'
        f'            <p class="sub"><a href="{url}">{url}</a></p>\n'
        f"          </td>\n"
        f"        </tr>\n"
        f"      </table>"
    )


# wraps a template's content in the shared email layout
def base_email(*, title: str, preheader: str, logo_url: str | None, content_html: str) -> str:
    # the anchor is inline-block so the centred cell can centre it, while the image
    # inside stays a block, which is what stops mail clients adding a stray baseline gap
    masthead = (
        f'<a href="https://qrew.com" style="display:inline-block;">'
        f'<img src="{logo_url}" alt="QREW" width="160" height="160"'
        ' style="display:block;border:none;width:160px;height:160px;" /></a>'
        if logo_url
        else '<a href="https://qrew.com" class="email-masthead_name">QREW</a>'
    )
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="x-apple-disable-message-reformatting" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="color-scheme" content="dark" />
    <meta name="supported-color-schemes" content="dark" />
    <title>{title}</title>
    <style type="text/css" rel="stylesheet" media="all">
      @import url("https://fonts.googleapis.com/css?family=Nunito+Sans:400,700&display=swap");

      body {{
        width: 100% !important;
        height: 100%;
        margin: 0;
        -webkit-text-size-adjust: none;
        background-color: #1A1A1A;
        color: #E7EBEF;
      }}

      a {{ color: #BF7318; }}
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
        color: #FFFFFF;
        font-size: 22px;
        font-weight: bold;
        text-align: left;
      }}

      p {{
        color: #E7EBEF;
        font-size: 16px;
        line-height: 1.625;
        margin: 0.4em 0 1.1875em;
      }}

      p.sub {{ font-size: 13px; color: #768293; }}

      .email-wrapper {{
        width: 100%;
        margin: 0;
        padding: 0;
        background-color: #1A1A1A;
      }}

      .email-content {{ width: 100%; margin: 0; padding: 0; }}

      .email-masthead {{
        padding: 32px 0 24px;
        text-align: center;
        background-color: #1A1A1A;
      }}

      .email-masthead_name {{
        font-size: 20px;
        font-weight: bold;
        color: #BF7318;
        text-decoration: none;
      }}

      .email-body {{ width: 100%; margin: 0; padding: 0; background-color: #1A1A1A; }}

      .email-body_inner {{
        width: 570px;
        margin: 0 auto;
        padding: 0;
        background-color: #171717;
        border: 1px solid #292929;
        border-radius: 8px;
      }}

      .email-footer {{
        width: 570px;
        margin: 0 auto;
        padding: 0;
        text-align: center;
        background-color: #1A1A1A;
      }}

      .email-footer p {{ color: #768293; }}
      .email-footer a {{ color: #BF7318; }}

      .content-cell {{ padding: 45px; }}

      .button {{
        background-color: #BF7318;
        border-top: 10px solid #BF7318;
        border-right: 18px solid #BF7318;
        border-bottom: 10px solid #BF7318;
        border-left: 18px solid #BF7318;
        display: inline-block;
        color: #FFFFFF !important;
        text-decoration: none;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(191,115,24,0.35);
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
        border-top: 1px solid #292929;
      }}

      @media only screen and (max-width: 600px) {{
        .email-body_inner, .email-footer {{ width: 100% !important; }}
        .button {{ width: 100% !important; text-align: center !important; }}
      }}
    </style>
  </head>
  <body>
    <span class="preheader">{preheader}</span>
    <table class="email-wrapper" width="100%" cellpadding="0" cellspacing="0" role="presentation">
      <tr>
        <td align="center">
          <table class="email-content" width="100%" cellpadding="0" cellspacing="0" role="presentation">

            <!-- Masthead -->
            <tr>
              <td class="email-masthead" align="center">
                {masthead}
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td class="email-body" width="570" cellpadding="0" cellspacing="0">
                <table class="email-body_inner" align="center" width="570" cellpadding="0" cellspacing="0" role="presentation">
                  <tr>
                    <td class="content-cell">
{content_html}
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
                      <p class="sub">QREW. All rights reserved.</p>
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
