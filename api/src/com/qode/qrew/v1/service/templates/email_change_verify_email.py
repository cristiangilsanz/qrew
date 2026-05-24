def email_change_verify_email(full_name: str, link: str, expire_hours: int) -> str:
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>Confirm your new email address</title>
    <style type="text/css">
      body {{ font-family: "Nunito Sans", Helvetica, Arial, sans-serif; background-color: #F2F4F6; color: #51545E; margin: 0; padding: 0; }}
      a {{ color: #3869D4; }}
      h1 {{ color: #333333; font-size: 22px; font-weight: bold; }}
      p {{ font-size: 16px; line-height: 1.625; margin: 0.4em 0 1.1875em; }}
      p.sub {{ font-size: 13px; color: #A8AAAF; }}
      .wrapper {{ width: 100%; background-color: #F2F4F6; padding: 25px 0; }}
      .inner {{ width: 570px; margin: 0 auto; background-color: #FFFFFF; padding: 45px; }}
      .button {{ background-color: #3869D4; border: 10px solid #3869D4; border-left-width: 18px; border-right-width: 18px; color: #FFF !important; text-decoration: none; border-radius: 3px; font-weight: bold; font-size: 15px; display: inline-block; }}
      .body-action {{ width: 100%; margin: 30px auto; text-align: center; }}
      .body-sub {{ margin-top: 25px; padding-top: 25px; border-top: 1px solid #EAEAEC; }}
    </style>
  </head>
  <body>
    <div class="wrapper">
      <div class="inner">
        <h1>Confirm your new email, {full_name.split(maxsplit=1)[0]}!</h1>
        <p>You recently requested to change the email address on your Qrew account to this one.</p>
        <p>Click the button below to confirm the change.</p>
        <div class="body-action">
          <a href="{link}" class="button" target="_blank">Confirm email change</a>
        </div>
        <p>This link expires in <strong>{expire_hours} hours</strong>.</p>
        <p>If you did not request this change, you can safely ignore this message.</p>
        <div class="body-sub">
          <p class="sub">If the button above doesn't work, copy and paste this URL into your browser:</p>
          <p class="sub"><a href="{link}">{link}</a></p>
        </div>
      </div>
    </div>
  </body>
</html>"""
