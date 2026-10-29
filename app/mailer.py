import smtplib
from email.message import EmailMessage
from .config import settings


def password_reset_email_configured() -> bool:
    return all((settings.smtp_host, settings.smtp_from_email))


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Reset your Performance Hub password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your Performance Hub password.\n\n"
        f"Use this link within 30 minutes to choose a new password:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(message)
