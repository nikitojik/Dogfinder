import math
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Listing, Photo
from app.models.listing import Kind, Status

VISUAL_WEIGHT = 0.6
GEO_WEIGHT = 0.2
TIME_WEIGHT = 0.2

GEO_SCALE_KM = 20.0
TIME_SCALE_DAYS = 30.0

MIN_VISUAL_SIMILARITY = 0.55
CANDIDATE_LIMIT = 50


def geo_score(distance_m: float | None) -> float:
    if distance_m is None:
        return 0.0
    return math.exp(-(distance_m / 1000) / GEO_SCALE_KM)


def time_score(a: datetime, b: datetime) -> float:
    days = abs((a - b).total_seconds()) / 86400
    return math.exp(-days / TIME_SCALE_DAYS)


def pick_query_photo(listing: Listing) -> Photo | None:
    with_embedding = [p for p in listing.photos if p.embedding is not None]
    if not with_embedding:
        return None
    primary = next((p for p in with_embedding if p.is_primary), None)
    return primary or with_embedding[0]


async def find_matches(listing: Listing, session: AsyncSession, limit: int = 10) -> list[dict]:
    query_photo = pick_query_photo(listing)
    if query_photo is None:
        return []

    opposite = Kind.FOUND if listing.kind == Kind.LOST else Kind.LOST
    similarity = (1 - Photo.embedding.cosine_distance(query_photo.embedding)).label("similarity")

    stmt = (
        select(Listing.id, similarity)
        .join(Photo, Photo.listing_id == Listing.id)
        .where(
            Listing.kind == opposite,
            Listing.status == Status.ACTIVE,
            Listing.id != listing.id,
            Photo.embedding.is_not(None),
        )
        .order_by(similarity.desc())
        .limit(CANDIDATE_LIMIT)
    )

    if listing.location is not None:
        stmt = stmt.add_columns(
            func.ST_Distance(Listing.location, listing.location).label("distance_m")
        )

    rows = (await session.execute(stmt)).all()

    best: dict[int, dict] = {}
    for row in rows:
        visual = float(row.similarity)
        if visual < MIN_VISUAL_SIMILARITY:
            continue
        if row.id in best and best[row.id]["visual"] >= visual:
            continue
        best[row.id] = {
            "visual": visual,
            "distance_m": getattr(row, "distance_m", None),
        }

    if not best:
        return []

    candidates = await session.scalars(
        select(Listing)
        .where(Listing.id.in_(best.keys()))
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
    )

    results = []
    for candidate in candidates:
        data = best[candidate.id]
        geo = geo_score(data["distance_m"])
        time_value = time_score(listing.happened_at, candidate.happened_at)

        score = VISUAL_WEIGHT * data["visual"] + GEO_WEIGHT * geo + TIME_WEIGHT * time_value

        results.append(
            {
                "listing": candidate,
                "score": score,
                "visual": data["visual"],
                "distance_m": data["distance_m"],
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]
