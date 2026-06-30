def email_change_alert_email(full_name: str, new_email: str) -> str:
    masked = new_email[:2] + "***@" + new_email.split("@", 1)[1]
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>Email change requested</title>
    <style type="text/css">
      body {{ font-family: "Nunito Sans", Helvetica, Arial, sans-serif; background-color: #F2F4F6; color: #51545E; margin: 0; padding: 0; }}
      a {{ color: #3869D4; }}
      h1 {{ color: #333333; font-size: 22px; font-weight: bold; }}
      p {{ font-size: 16px; line-height: 1.625; margin: 0.4em 0 1.1875em; }}
      p.sub {{ font-size: 13px; color: #A8AAAF; }}
      .wrapper {{ width: 100%; background-color: #F2F4F6; padding: 25px 0; }}
      .inner {{ width: 570px; margin: 0 auto; background-color: #FFFFFF; padding: 45px; }}
    </style>
  </head>
  <body>
    <div class="wrapper">
      <div class="inner">
        <h1>Email change requested</h1>
        <p>Hi {full_name.split(maxsplit=1)[0]},</p>
        <p>A request was made to change the email address on your Qrew account to <strong>{masked}</strong>.</p>
        <p>If this was you, no further action is needed — you will receive a confirmation link at the new address.</p>
        <p>If you did not make this request, please <a href="mailto:support@qrew.com">contact support</a> immediately.</p>
        <p class="sub">Qrew &mdash; All rights reserved.</p>
      </div>
    </div>
  </body>
</html>"""
