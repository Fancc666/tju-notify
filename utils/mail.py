from __future__ import annotations

import smtplib
import traceback
from email.message import EmailMessage

from .printer import print_flush, RED, GREEN, YELLOW, RESET
from .EnvironTool import config


def _get_smtp_config() -> dict | None:
    """Read SMTP configuration from environment variables.

    Returns a dict with smtp_server, smtp_port, smtp_user, smtp_pass,
    admin_mail, or None if required values are missing.
    """
    smtp_server = config.get("SMTP_SERVER", "")
    smtp_user = config.get("SMTP_USER", "")
    smtp_pass = config.get("SMTP_PASSWORD", "")
    admin_mail = config.get("ADMIN_MAIL", "")

    if not all([smtp_server, smtp_user, smtp_pass, admin_mail]):
        return None

    try:
        smtp_port = int(config.get("SMTP_PORT", "587"))
    except (TypeError, ValueError):
        smtp_port = 587

    return {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_pass": smtp_pass,
        "admin_mail": admin_mail,
    }


def send_info_mail(subject: str, body: str) -> bool:
    """Send an info email to the configured admin address.

    Uses STARTTLS for port 587 (default) or implicit SSL for port 465.
    Returns True on success, False on any failure (after logging the error).
    """
    config = _get_smtp_config()
    if config is None:
        print_flush(f"{YELLOW}==> Mail notification skipped: SMTP config incomplete{RESET}")
        return False

    try:
        msg = EmailMessage()
        msg["From"] = config["smtp_user"]
        msg["To"] = config["admin_mail"]
        msg["Subject"] = f"[Studyroom] {subject}"
        msg.set_content(body)

        if config["smtp_port"] == 465:
            server = smtplib.SMTP_SSL(
                config["smtp_server"], config["smtp_port"], timeout=15
            )
        else:
            server = smtplib.SMTP(
                config["smtp_server"], config["smtp_port"], timeout=15
            )
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(config["smtp_user"], config["smtp_pass"])
        server.send_message(msg)
        server.quit()

        print_flush(f"{GREEN}==> Alert email sent to {config['admin_mail']}{RESET}")
        return True

    except Exception as e:
        print_flush(f"{RED}==> Failed to send alert email: {e}{RESET}")
        traceback.print_exc()
        return False
