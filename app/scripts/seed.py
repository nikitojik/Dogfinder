"""Наполнение базы демонстрационными данными.

Загружает фотографии собак из Dog CEO API и создаёт объявления со случайными
координатами вокруг заданного центра. Дополнительно использует парные снимки
из experiments/data, чтобы в базе были настоящие совпадения для матчинга.

Запуск:
    NOTIFICATIONS_ENABLED=false uv run python -m app.scripts.seed
"""

import asyncio
import math
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.ml.embedder import get_embedder
from app.models import Listing, Photo, User
from app.models.listing import Kind, Sex, Size, Status
from app.services.geo_utils import make_point
from app.services.storage import build_thumb_key, make_thumbnail, upload_bytes

# Центр области, вокруг которого разбрасываются объявления.
CENTER_LAT, CENTER_LON = 61.0667, 42.1000
SPREAD_KM = 12.0

RANDOM_LISTINGS = 200
PAIRS_DIR = Path(__file__).resolve().parent.parent.parent / "experiments" / "data"

DOG_API = "https://dog.ceo/api/breeds/image/random"
DOWNLOAD_CONCURRENCY = 8

DEMO_USERS = [
    ("anna", "Анна Смирнова"),
    ("sergey", "Сергей Ковалёв"),
    ("marina", "Марина Титова"),
    ("pavel", "Павел Егоров"),
    ("olga", "Ольга Верещагина"),
    ("dmitry", "Дмитрий Соколов"),
    ("elena", "Елена Ильина"),
    ("artem", "Артём Белов"),
]

LOST_TITLES = [
    "Пропал {breed}",
    "Потерялась собака, {breed}",
    "Убежал {breed}, помогите найти",
    "Пропала собака в районе {place}",
    "Ищем {breed}, пропал {place}",
]

FOUND_TITLES = [
    "Найден {breed}",
    "Найдена собака у {place}",
    "Подобрали {breed}, ищем хозяина",
    "Бегает собака возле {place}",
    "Найден пёс, похож на {breed}",
]

PLACES = [
    "вокзала",
    "школы №2",
    "парка",
    "рынка",
    "автостанции",
    "набережной",
    "стадиона",
    "поликлиники",
    "детского сада",
    "торгового центра",
]

LOST_DESCRIPTIONS = [
    "Убежал во время прогулки, испугался салюта. Отзывается на кличку.",
    "Пропал из двора, калитка была открыта. Очень пугливый, к чужим не подходит.",
    "Потерялся вечером, был в синем ошейнике. Просьба звонить в любое время.",
    "Сорвался с поводка у магазина. Собака домашняя, на улице растеряется.",
    "",
]

FOUND_DESCRIPTIONS = [
    "Собака ухоженная, явно домашняя. Держим у себя, ищем хозяина.",
    "Бегает вторые сутки, к людям подходит охотно. Ошейника нет.",
    "Подобрали у дороги, отвезли к ветеринару. Здоров, чипа нет.",
    "Сидит возле подъезда, никуда не уходит. Похоже, потерялся.",
    "",
]

COLORS = [
    "рыжий",
    "чёрный",
    "белый",
    "серый",
    "palевый",
    "чёрно-белый",
    "рыже-белый",
    "коричневый",
    "тигровый",
]

SIZES = [Size.SMALL, Size.MEDIUM, Size.LARGE]
SEXES = [Sex.MALE, Sex.FEMALE, Sex.UNKNOWN]


def breed_from_url(url: str) -> str:
    """Извлекает породу из адреса вида .../breeds/hound-afghan/n02088094_1003.jpg"""
    try:
        slug = url.split("/breeds/")[1].split("/")[0]
    except IndexError:
        return "дворняга"

    parts = slug.split("-")
    if len(parts) == 1:
        return parts[0].capitalize()
    return f"{parts[1].capitalize()} {parts[0]}"


def random_point() -> tuple[float, float]:
    """Случайная точка в радиусе SPREAD_KM от центра."""
    lat_delta = SPREAD_KM / 111.32
    lon_delta = SPREAD_KM / (111.32 * math.cos(math.radians(CENTER_LAT)))

    return (
        CENTER_LAT + random.uniform(-lat_delta, lat_delta),
        CENTER_LON + random.uniform(-lon_delta, lon_delta),
    )


def random_date(max_days: int = 90) -> datetime:
    return datetime.now(UTC) - timedelta(
        days=random.randint(0, max_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


async def fetch_image_urls(count: int) -> list[str]:
    """Забирает список адресов фотографий из Dog CEO API."""
    urls: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        while len(urls) < count:
            batch = min(50, count - len(urls))
            response = await client.get(f"{DOG_API}/{batch}")
            response.raise_for_status()
            urls.extend(response.json()["message"])
            print(f"  получено адресов: {len(urls)} / {count}")

    return urls[:count]


async def download(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception:
        return None


async def download_all(urls: list[str]) -> list[tuple[str, bytes]]:
    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
    result: list[tuple[str, bytes]] = []

    async with httpx.AsyncClient() as client:

        async def worker(url: str) -> None:
            async with semaphore:
                data = await download(client, url)
                if data is not None:
                    result.append((url, data))
                if len(result) % 25 == 0 and result:
                    print(f"  скачано: {len(result)} / {len(urls)}")

        await asyncio.gather(*(worker(url) for url in urls))

    return result


def random_phone() -> str:
    return f"+7 900 {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"


async def ensure_users(session) -> list[User]:
    """Создаёт демонстрационных пользователей, если их ещё нет."""
    users = []

    for login, name in DEMO_USERS:
        email = f"{login}@dogfinder.demo"
        existing = await session.scalar(select(User).where(User.email == email))

        if existing is not None:
            users.append(existing)
            continue

        user = User(
            email=email,
            name=name,
            phone=random_phone(),
            hashed_password=hash_password("demopassword"),
            locale=random.choice(["ru", "en"]),
        )
        session.add(user)
        users.append(user)

    await session.commit()
    for user in users:
        await session.refresh(user)

    return users


def store_photo(listing_id: int, data: bytes) -> tuple[str, str | None]:
    """Кладёт оригинал и превью в объектное хранилище."""
    object_key = f"listings/{listing_id}/{uuid.uuid4().hex}.jpg"
    upload_bytes(object_key, data, "image/jpeg")

    thumb_key = None
    try:
        thumb = make_thumbnail(data)
        thumb_key = build_thumb_key(object_key)
        upload_bytes(thumb_key, thumb, "image/jpeg")
    except Exception:
        pass

    return object_key, thumb_key


def build_listing(
    owner: User,
    kind: Kind,
    breed: str,
    happened_at: datetime,
    lat: float,
    lon: float,
) -> Listing:
    place = random.choice(PLACES)
    template = random.choice(LOST_TITLES if kind == Kind.LOST else FOUND_TITLES)
    descriptions = LOST_DESCRIPTIONS if kind == Kind.LOST else FOUND_DESCRIPTIONS

    return Listing(
        owner_id=owner.id,
        kind=kind,
        status=Status.ACTIVE,
        title=template.format(breed=breed, place=place),
        description=random.choice(descriptions) or None,
        happened_at=happened_at,
        breed=breed,
        color=random.choice(COLORS),
        size=random.choice(SIZES),
        sex=random.choice(SEXES),
        location=make_point(lat, lon),
    )


async def create_with_photo(
    session,
    owner: User,
    kind: Kind,
    breed: str,
    happened_at: datetime,
    lat: float,
    lon: float,
    image: bytes,
    embedder,
) -> None:
    listing = build_listing(owner, kind, breed, happened_at, lat, lon)
    session.add(listing)
    await session.flush()

    object_key, thumb_key = await asyncio.to_thread(store_photo, listing.id, image)
    result = await asyncio.to_thread(embedder.process, image)

    session.add(
        Photo(
            listing_id=listing.id,
            object_key=object_key,
            thumb_key=thumb_key,
            content_type="image/jpeg",
            size_bytes=len(image),
            is_primary=True,
            sort_order=0,
            embedding=result["embedding"],
            bbox=result["box"],
            dog_detected=result["dog_detected"],
        )
    )


async def seed_random(session, users: list[User], embedder) -> None:
    print(f"Запрашиваем {RANDOM_LISTINGS} адресов фотографий…")
    urls = await fetch_image_urls(RANDOM_LISTINGS)

    print("Скачиваем изображения…")
    images = await download_all(urls)
    print(f"Скачано {len(images)} изображений")

    print("Создаём объявления…")
    for index, (url, data) in enumerate(images, start=1):
        lat, lon = random_point()

        await create_with_photo(
            session=session,
            owner=random.choice(users),
            kind=random.choice([Kind.LOST, Kind.FOUND]),
            breed=breed_from_url(url),
            happened_at=random_date(),
            lat=lat,
            lon=lon,
            image=data,
            embedder=embedder,
        )

        if index % 20 == 0:
            await session.commit()
            print(f"  создано: {index} / {len(images)}")

    await session.commit()


async def seed_pairs(session, users: list[User], embedder) -> int:
    """Создаёт пары объявлений из парных снимков в experiments/data."""
    if not PAIRS_DIR.exists():
        print(f"Папки {PAIRS_DIR} нет, пары пропускаем")
        return 0

    suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    groups: dict[str, list[Path]] = {}

    for path in sorted(PAIRS_DIR.iterdir()):
        if path.suffix.lower() not in suffixes:
            continue
        groups.setdefault(path.stem.split("_")[0], []).append(path)

    pairs = [(key, files) for key, files in groups.items() if len(files) >= 2]
    print(f"Найдено пар: {len(pairs)}")

    for key, files in pairs:
        lost_at = random_date(max_days=20)
        found_at = lost_at + timedelta(days=random.randint(1, 5))

        lat, lon = random_point()
        # Находка недалеко от места пропажи
        found_lat = lat + random.uniform(-0.02, 0.02)
        found_lon = lon + random.uniform(-0.03, 0.03)

        owner, finder = random.sample(users, 2)
        breed = random.choice(["Метис", "Дворняга", "Лабрадор", "Овчарка", "Спаниель"])

        await create_with_photo(
            session,
            owner,
            Kind.LOST,
            breed,
            lost_at,
            lat,
            lon,
            files[0].read_bytes(),
            embedder,
        )
        await create_with_photo(
            session,
            finder,
            Kind.FOUND,
            breed,
            found_at,
            found_lat,
            found_lon,
            files[1].read_bytes(),
            embedder,
        )

        await session.commit()
        print(f"  пара {key} создана")

    return len(pairs)


async def main() -> None:
    if settings.notifications_enabled:
        print("Уведомления включены. Запусти с NOTIFICATIONS_ENABLED=false,")
        print("иначе владельцы получат сотни писем.")
        return

    random.seed(42)

    print("Загружаем модели…")
    embedder = await asyncio.to_thread(get_embedder)

    async with SessionLocal() as session:
        users = await ensure_users(session)
        print(f"Пользователей: {len(users)}")

        pairs = await seed_pairs(session, users, embedder)
        await seed_random(session, users, embedder)

        total = await session.scalar(select(Listing.id).order_by(Listing.id.desc()).limit(1))

    print()
    print(f"Готово. Пар для матчинга: {pairs}, всего объявлений в базе: около {total}")


if __name__ == "__main__":
    asyncio.run(main())
