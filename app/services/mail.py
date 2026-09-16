import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


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
