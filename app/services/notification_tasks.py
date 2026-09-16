import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import Listing, Response
from app.models.notification import NotificationKind
from app.services.notifications import deliver, is_throttled, reserve

logger = logging.getLogger(__name__)


async def notify_new_response(response_id: int) -> None:
    try:
        async with SessionLocal() as session:
            response = await session.scalar(
                select(Response)
                .where(Response.id == response_id)
                .options(
                    selectinload(Response.author),
                    selectinload(Response.listing).selectinload(Listing.owner),
                )
            )
            if response is None:
                return

            owner = response.listing.owner

            if await is_throttled(owner.id, session):
                logger.info("Лимит писем исчерпан для user_id=%s", owner.id)
                return

            notification = await reserve(
                user_id=owner.id,
                kind=NotificationKind.NEW_RESPONSE,
                listing_id=response.listing_id,
                subject_id=response.id,
                session=session,
            )
            if notification is None:
                return

            await deliver(
                notification=notification,
                user=owner,
                template="new_response",
                subject=f"Отклик на объявление «{response.listing.title}»",
                session=session,
                author_name=response.author.name,
                listing=response.listing,
                message=response.message,
                phone=response.contact_phone or response.author.phone,
            )
    except Exception:
        logger.exception("Не удалось уведомить об отклике response_id=%s", response_id)
