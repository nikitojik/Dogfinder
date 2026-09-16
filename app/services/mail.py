import logging
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "email"

jinja_env = Environment(
    loader=FileSystemLoader(EMAIL_TEMPLATES),
    autoescape=select_autoescape(["html"]),
)


def render_email(name: str, **context) -> tuple[str, str]:
    html = jinja_env.get_template(f"{name}.html").render(base_url=settings.base_url, **context)
    text = jinja_env.get_template(f"{name}.txt").render(base_url=settings.base_url, **context)
    return html, text


async def send_email(to: str, subject: str, html: str, text: str) -> bool:
    if not settings.notifications_enabled:
        logger.info("Уведомления отключены, письмо для %s не отправлено", to)
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_tls,
            timeout=15,
        )
    except Exception:
        logger.exception("Не удалось отправить письмо на %s", to)
        return False

    logger.info("Письмо отправлено на %s: %s", to, subject)
    return True
