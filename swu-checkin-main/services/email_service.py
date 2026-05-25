import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

CHINA_TZ = timezone(timedelta(hours=8))


def generate_code(length=6):
    return "".join(random.choices(string.digits, k=length))


def send_email(config, to_email, code):
    """Send verification code via SMTP. Returns (success, error_message)."""
    if not config.get("SMTP_USER") or not config.get("SMTP_PASSWORD"):
        # In development mode without SMTP, print to console
        print(f"[DEV] Verification code for {to_email}: {code}")
        return True, None

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "mimimi签到系统 - 邮箱验证码"
        msg["From"] = config["SMTP_FROM"] or config["SMTP_USER"]
        msg["To"] = to_email

        html = f"""\
<html>
<body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;">
  <h2 style="color:#22C55E;">签到系统</h2>
  <p>欢迎参与内测，mimi对你说：</
  <p>你的邮箱验证码为：</p>
  <p style="font-size:32px;font-weight:bold;color:#22C55E;letter-spacing:4px;">{code}</p>
  <p style="color:#64748B;">验证码 10 分钟内有效，请勿转发给他人。</p>
</body>
</html>"""
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"]) as server:
            server.starttls()
            server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "邮箱服务认证失败，请联系管理员"
    except smtplib.SMTPConnectError:
        return False, "无法连接邮箱服务器，请稍后重试"
    except Exception as e:
        return False, f"邮件发送失败: {str(e)}"
