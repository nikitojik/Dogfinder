import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import Listing, Response, User
from app.models.notification import NotificationKind
from app.services.matching import find_matches
from app.services.notifications import deliver, is_throttled, reserve

logger = logging.getLogger(__name__)

MATCH_NOTIFY_THRESHOLD = 0.70
MAX_MATCHES_PER_LISTING = 3


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


def format_distance(meters: float | None) -> str | None:
    if meters is None:
        return None
    return f"{round(meters)} м" if meters < 1000 else f"{meters / 1000:.1f} км"


def pick_photo_url(listing: Listing) -> str | None:
    if not listing.photos:
        return None
    primary = next((p for p in listing.photos if p.is_primary), None)
    return (primary or listing.photos[0]).url


async def _send_match_email(
    recipient: User,
    listing: Listing,
    match: Listing,
    visual: float,
    distance_m: float | None,
    session,
) -> None:
    if await is_throttled(recipient.id, session):
        logger.info("Лимит писем исчерпан для user_id=%s", recipient.id)
        return

    notification = await reserve(
        user_id=recipient.id,
        kind=NotificationKind.NEW_MATCH,
        listing_id=listing.id,
        subject_id=match.id,
        session=session,
    )
    if notification is None:
        return

    await deliver(
        notification=notification,
        user=recipient,
        template="new_match",
        subject=f"Похожее объявление: {match.title}",
        session=session,
        listing=listing,
        match=match,
        percent=round(visual * 100),
        distance=format_distance(distance_m),
        photo_url=pick_photo_url(match),
    )


async def notify_matches_for_listing(listing_id: int) -> None:
    try:
        async with SessionLocal() as session:
            listing = await session.scalar(
                select(Listing)
                .where(Listing.id == listing_id)
                .options(selectinload(Listing.owner), selectinload(Listing.photos))
            )
            if listing is None:
                return

            matches = await find_matches(listing, session, limit=MAX_MATCHES_PER_LISTING)

            for item in matches:
                if item["score"] < MATCH_NOTIFY_THRESHOLD:
                    continue

                candidate = item["listing"]

                await _send_match_email(
                    recipient=listing.owner,
                    listing=listing,
                    match=candidate,
                    visual=item["visual"],
                    distance_m=item["distance_m"],
                    session=session,
                )

                await _send_match_email(
                    recipient=candidate.owner,
                    listing=candidate,
                    match=listing,
                    visual=item["visual"],
                    distance_m=item["distance_m"],
                    session=session,
                )
    except Exception:
        logger.exception("Не удалось разослать уведомления о совпадениях listing_id=%s", listing_id)
