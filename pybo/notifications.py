"""Delivery adapters for identity-verification messages."""

from email.message import EmailMessage
import json
import smtplib
import ssl
from urllib.request import Request, urlopen


def send_email_code(config, recipient, purpose, code):
    host = config.get("SMTP_HOST")
    sender = config.get("SMTP_FROM_EMAIL") or config.get("SMTP_USERNAME")
    if not host or not sender or not recipient:
        return False
    message = EmailMessage()
    message["Subject"] = f"Friendary {purpose} 인증번호"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(f"인증번호는 {code}입니다. 10분 안에 입력해 주세요.")
    with smtplib.SMTP(host, config.get("SMTP_PORT", 587), timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        username = config.get("SMTP_USERNAME")
        if username:
            smtp.login(username, config.get("SMTP_PASSWORD", ""))
        smtp.send_message(message)
    return True


def send_sms_code(config, phone, code):
    """Send through a provider-neutral JSON webhook.

    The configured endpoint receives {to, message}; Authorization uses Bearer token.
    """
    endpoint = config.get("SMS_API_URL")
    if not endpoint:
        return False
    payload = json.dumps({"to": phone, "message": f"[Friendary] 인증번호 {code}"}).encode()
    headers = {"Content-Type": "application/json"}
    token = config.get("SMS_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(endpoint, data=payload, headers=headers, method="POST"), timeout=10):
        return True

