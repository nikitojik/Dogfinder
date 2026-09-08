from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, null, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.models import Listing
from app.models.listing import Kind, Size, Status
from app.schemas.listing import ListingCreate, ListingPage, ListingRead, ListingUpdate
from app.services.geo import make_point

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
async def create_listing(data: ListingCreate, user: CurrentUser, session: SessionDep) -> Listing:
    payload = data.model_dump(exclude={"lat", "lon"})
    location = (
        make_point(data.lat, data.lon) if data.lat is not None and data.lon is not None else None
    )
    listing = Listing(**payload, owner_id=user.id, location=location)
    session.add(listing)
    await session.commit()

    result = await session.scalar(
        select(Listing)
        .where(Listing.id == listing.id)
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
    )
    return result


@router.get("", response_model=ListingPage)
async def list_listings(
    session: SessionDep,
    kind: Kind | None = None,
    listing_status: Annotated[Status | None, Query(alias="status")] = Status.ACTIVE,
    breed: str | None = None,
    size: Size | None = None,
    since: datetime | None = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=500)] = None,
    sort: Annotated[str, Query(pattern="^(date|distance)$")] = "date",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListingPage:
    conditions = []
    if kind is not None:
        conditions.append(Listing.kind == kind)
    if listing_status is not None:
        conditions.append(Listing.status == listing_status)
    if breed is not None:
        conditions.append(Listing.breed.ilike(f"%{breed}%"))
    if size is not None:
        conditions.append(Listing.size == size)
    if since is not None:
        conditions.append(Listing.happened_at >= since)

    has_point = lat is not None and lon is not None
    if (lat is None) != (lon is None):
        raise HTTPException(status_code=400, detail="Нужны обе координаты: lat и lon")
    if radius_km is not None and not has_point:
        raise HTTPException(status_code=400, detail="Радиус без координат не имеет смысла")

    origin = make_point(lat, lon) if has_point else None

    if origin is not None and radius_km is not None:
        conditions.append(func.ST_DWithin(Listing.location, origin, radius_km * 1000))

    total = await session.scalar(select(func.count()).select_from(Listing).where(*conditions))

    distance = (
        func.ST_Distance(Listing.location, origin).label("distance_m")
        if origin is not None
        else null().label("distance_m")
    )

    query = select(Listing, distance).where(*conditions)

    if sort == "distance" and origin is not None:
        query = query.order_by(distance.asc().nulls_last())
    else:
        query = query.order_by(Listing.happened_at.desc())

    rows = await session.execute(
        query.options(selectinload(Listing.owner), selectinload(Listing.photos))
        .limit(limit)
        .offset(offset)
    )

    items = []
    for listing, distance_m in rows:
        item = ListingRead.model_validate(listing)
        item.distance_m = round(distance_m) if distance_m is not None else None
        items.append(item)

    return ListingPage(items=list(items), total=total or 0, limit=limit, offset=offset)


@router.get("/{listing_id}", response_model=ListingRead)
async def get_listing(listing_id: int, session: SessionDep) -> Listing:
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return listing


@router.patch("/{listing_id}", response_model=ListingRead)
async def update_listing(
    listing_id: int, data: ListingUpdate, user: CurrentUser, session: SessionDep
) -> Listing:
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
    )
    payload = data.model_dump(exclude_unset=True)
    lat = payload.pop("lat", None)
    lon = payload.pop("lon", None)
    for field, value in payload.items():
        setattr(listing, field, value)

    if lat is not None and lon is not None:
        listing.location = make_point(lat, lon)

    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Нельзя редактировать чужое объявление")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)

    await session.commit()
    await session.refresh(listing, attribute_names=["updated_at"])
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(listing_id: int, user: CurrentUser, session: SessionDep) -> None:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Нельзя удалить чужое объявление")

    listing.status = Status.ARCHIVED
    await session.commit()
