import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, User
from app.models.notification import NotificationKind
from app.services.mail import render_email, send_email

logger = logging.getLogger(__name__)

DAILY_LIMIT = 10


async def is_throttled(user_id: int, session: AsyncSession) -> bool:
    since = datetime.now(UTC) - timedelta(days=1)
    count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.created_at >= since,
            Notification.sent.is_(True),
        )
    )
    return bool(count and count >= DAILY_LIMIT)


async def reserve(
    user_id: int,
    kind: NotificationKind,
    listing_id: int,
    subject_id: int,
    session: AsyncSession,
) -> Notification | None:
    notification = Notification(
        user_id=user_id, kind=kind, listing_id=listing_id, subject_id=subject_id
    )
    session.add(notification)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.info(
            "Уведомление %s для listing_id=%s subject_id=%s уже было",
            kind.value,
            listing_id,
            subject_id,
        )
        return None

    return notification


async def deliver(
    notification: Notification,
    user: User,
    template: str,
    subject: str,
    session: AsyncSession,
    **context,
) -> bool:
    html, text = render_email(template, locale=user.locale, owner_name=user.name, **context)
    ok = await send_email(to=user.email, subject=subject, html=html, text=text)

    if ok:
        notification.sent = True
        await session.commit()

    return ok
