import asyncio
import logging

from sqlalchemy import update

from app.db import SessionLocal
from app.ml.embedder import get_embedder
from app.models import Photo
from app.services.storage import (
    build_thumb_key,
    download_object,
    make_thumbnail,
    upload_bytes,
)

logger = logging.getLogger(__name__)


async def process_photo(photo_id: int, object_key: str) -> None:
    try:
        data = await asyncio.to_thread(download_object, object_key)
    except Exception:
        logger.exception("Не удалось скачать фото photo_id=%s", photo_id)
        return

    thumb_key = None
    try:
        thumb = await asyncio.to_thread(make_thumbnail, data)
        thumb_key = build_thumb_key(object_key)
        await asyncio.to_thread(upload_bytes, thumb_key, thumb, "image/jpeg")
    except Exception:
        logger.exception("Не удалось создать превью для photo_id=%s", photo_id)

    values = {}
    if thumb_key:
        values["thumb_key"] = thumb_key

    try:
        embedder = await asyncio.to_thread(get_embedder)
        result = await asyncio.to_thread(embedder.process, data)
        values["embedding"] = result["embedding"]
        values["bbox"] = result["box"]
        values["dog_detected"] = result["dog_detected"]
    except Exception:
        logger.exception("Не удалось посчитать эмбеддинг для photo_id=%s", photo_id)

    if not values:
        return

    async with SessionLocal() as session:
        await session.execute(update(Photo).where(Photo.id == photo_id).values(**values))
        await session.commit()

    logger.info("Фото photo_id=%s обработано: %s", photo_id, ", ".join(values))
