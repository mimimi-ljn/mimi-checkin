import random
import string

import requests


def generate_code(length=6):
    return "".join(random.choices(string.digits, k=length))


def send_email(config, to_email, code):
    """
    Send verification code via Resend API.
    Falls back to console output if no API key configured.
    Returns (success, error_message).
    """
    api_key = config.get("RESEND_API_KEY", "")

    html_body = f"""\
<html>
<body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;">
  <h2 style="color:#EAB308;">MIMI签到系统</h2>
  <p>MIMI说：雷猴啊，欢迎参与内测，这是你的邮箱验证码：</p>
  <p style="font-size:32px;font-weight:bold;color:#EAB308;letter-spacing:4px;">{code}</p>
  <p style="color:#64748B;">验证码 10 分钟内有效，请勿转发给他人。</p>
  <hr style="border-color:#E5E7EB;">
  <p style="color:#94A3B8;font-size:12px;">本邮件由系统自动发送，无需回复。</p>
</body>
</html>"""

    if not api_key:
        print(f"[DEV] Verification code for {to_email}: {code}")
        return True, None

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "MIMI签到 <noreply@mail.twelvemi-checkin.cc.cd>",
                "to": [to_email],
                "subject": "MIMI签到系统 - 邮箱验证码",
                "html": html_body,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return True, None
        error_detail = r.json().get("message", r.text)
        return False, f"邮件发送失败: {error_detail}"
    except Exception as e:
        return False, f"邮件发送失败: {str(e)}"
