import asyncio
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.db import SessionLocal

COUNT = 100_000
CENTER_LAT, CENTER_LON = 61.0667, 42.1000
SPREAD_DEG = 8.0


async def main() -> None:
    async with SessionLocal() as session:
        owner_id = await session.scalar(text("SELECT id FROM users LIMIT 1"))
        if owner_id is None:
            print("Нет пользователей, сначала зарегистрируй кого-нибудь")
            return

        rows = []
        now = datetime.now(UTC)
        for i in range(COUNT):
            lat = CENTER_LAT + random.uniform(-SPREAD_DEG, SPREAD_DEG)
            lon = CENTER_LON + random.uniform(-SPREAD_DEG, SPREAD_DEG)
            happened = now - timedelta(days=random.randint(0, 365))
            kind = random.choice(["LOST", "FOUND"])
            rows.append(
                f"({owner_id}, '{kind}', 'ACTIVE', 'Тестовое объявление {i}', "
                f"'{happened.isoformat()}', 'UNKNOWN', "
                f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography, now(), now())"
            )

        batch = 5000
        for start in range(0, COUNT, batch):
            chunk = ",".join(rows[start : start + batch])
            await session.execute(
                text(
                    "INSERT INTO listings "
                    "(owner_id, kind, status, title, happened_at, sex, "
                    "location, created_at, updated_at) "
                    f"VALUES {chunk}"
                )
            )
            await session.commit()
            print(f"{start + batch} / {COUNT}")


if __name__ == "__main__":
    asyncio.run(main())
