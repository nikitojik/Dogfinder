from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.models import Listing
from app.models.listing import Kind, Size, Status
from app.schemas.listing import ListingCreate, ListingPage, ListingRead, ListingUpdate

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
async def create_listing(data: ListingCreate, user: CurrentUser, session: SessionDep) -> Listing:
    listing = Listing(**data.model_dump(), owner_id=user.id)
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

    total = await session.scalar(select(func.count()).select_from(Listing).where(*conditions))

    items = await session.scalars(
        select(Listing)
        .where(*conditions)
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
        .order_by(Listing.happened_at.desc())
        .limit(limit)
        .offset(offset)
    )

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
