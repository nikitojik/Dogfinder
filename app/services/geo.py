import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GeocodeCache

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DogFinder/0.1 (https://github.com/nikitojik/Dogfinder)"
REQUEST_TIMEOUT = 10.0

_rate_limit = asyncio.Semaphore(1)
_last_request_at = 0.0


def normalize_query(value: str) -> str:
    return " ".join(value.lower().split())


async def _fetch_from_nominatim(query: str) -> dict | None:
    global _last_request_at

    async with _rate_limit:
        elapsed = asyncio.get_event_loop().time() - _last_request_at
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(
                    NOMINATIM_URL,
                    params={"q": query, "format": "json", "limit": 1},
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                results = response.json()
        except (httpx.HTTPError, ValueError):
            logger.exception("Ошибка запроса к Nominatim: %s", query)
            return None
        finally:
            _last_request_at = asyncio.get_event_loop().time()

    if not results:
        return None

    first = results[0]
    return {
        "lat": float(first["lat"]),
        "lon": float(first["lon"]),
        "display_name": first.get("display_name"),
    }


async def geocode(address: str, session: AsyncSession) -> dict | None:
    query = normalize_query(address)
    if not query:
        return None

    cached = await session.scalar(select(GeocodeCache).where(GeocodeCache.query == query))
    if cached is not None:
        if cached.lat is None:
            return None
        return {
            "lat": cached.lat,
            "lon": cached.lon,
            "display_name": cached.display_name,
        }

    result = await _fetch_from_nominatim(query)

    entry = GeocodeCache(
        query=query,
        lat=result["lat"] if result else None,
        lon=result["lon"] if result else None,
        display_name=result["display_name"] if result else None,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()

    return result
