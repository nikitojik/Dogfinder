import asyncio
import logging

from sqlalchemy import update

from app.db import SessionLocal
from app.models import Photo
from app.services.storage import (
    build_thumb_key,
    download_object,
    make_thumbnail,
    upload_bytes,
)

logger = logging.getLogger(__name__)


async def generate_thumbnail(photo_id: int, object_key: str) -> None:
    try:
        data = await asyncio.to_thread(download_object, object_key)
        thumb = await asyncio.to_thread(make_thumbnail, data)
        thumb_key = build_thumb_key(object_key)
        await asyncio.to_thread(upload_bytes, thumb_key, thumb, "image/jpeg")

        async with SessionLocal() as session:
            await session.execute(
                update(Photo).where(Photo.id == photo_id).values(thumb_key=thumb_key)
            )
            await session.commit()
    except Exception:
        logger.exception("Не удалось создать превью для photo_id=%s", photo_id)
