import smtplib
from email.message import EmailMessage


def send_email_alert(config: dict, to_email: str, subject: str, body: str) -> bool:
    host = config.get("SMTP_HOST")
    sender = config.get("MAIL_FROM")
    if not (host and sender and to_email):
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(host, config.get("SMTP_PORT", 587), timeout=15) as server:
            if config.get("SMTP_USE_TLS", True):
                server.starttls()
            username = config.get("SMTP_USERNAME")
            password = config.get("SMTP_PASSWORD")
            if username and password:
                server.login(username, password)
            server.send_message(message)
        return True
    except Exception:
        return False
