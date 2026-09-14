import asyncio
import logging

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Photo
from app.services.photo_tasks import process_photo

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("app").setLevel(logging.INFO)


async def main() -> None:
    async with SessionLocal() as session:
        photos = await session.scalars(
            select(Photo).where(Photo.embedding.is_(None)).order_by(Photo.id)
        )
        items = list(photos)

    print(f"Фотографий без эмбеддинга: {len(items)}")

    for index, photo in enumerate(items, start=1):
        await process_photo(photo.id, photo.object_key)
        print(f"{index} / {len(items)}")


if __name__ == "__main__":
    asyncio.run(main())
