from __future__ import annotations

import os
import smtplib
import traceback
from datetime import datetime
from email.message import EmailMessage

from .util import print_flush, RED, GREEN, YELLOW, RESET


def _get_smtp_config() -> dict | None:
    """Read SMTP configuration from environment variables.

    Returns a dict with smtp_server, smtp_port, smtp_user, smtp_pass,
    admin_mail, or None if required values are missing.
    """
    smtp_server = os.getenv("STMP_SERVER")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    admin_mail = os.getenv("ADMIN_MAIL")

    if not all([smtp_server, smtp_user, smtp_pass, admin_mail]):
        return None

    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except (TypeError, ValueError):
        smtp_port = 587

    return {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_pass": smtp_pass,
        "admin_mail": admin_mail,
    }


def send_alert_mail(subject: str, body: str) -> bool:
    """Send an alert email to the configured admin address.

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


def build_failure_report(
    task_name: str,
    error: Exception | None,
    extra_info: str | None = None,
) -> str:
    """Build a plain-text failure report for email delivery.

    Parameters:
        task_name:  Human-readable name of the task that failed.
        error:      The exception that caused the failure (may be None).
        extra_info: Optional additional context to include.

    Returns a string suitable for use as an email body.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "Studyroom Refresher — Task Failure Report",
        "=" * 50,
        f"Time:  {now}",
        f"Task:  {task_name}",
    ]

    if error is not None:
        lines.append(f"Error: {type(error).__name__}: {error}")
        tb = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        lines.append("")
        lines.append("Full Traceback:")
        lines.append("-" * 50)
        lines.append(tb)

    if extra_info:
        lines.append("")
        lines.append("Additional Info:")
        lines.append("-" * 50)
        lines.append(extra_info)

    lines.append("")
    lines.append("=" * 50)
    lines.append("This is an automated alert from the Studyroom Refresher service.")

    return "\n".join(lines)
