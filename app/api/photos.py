import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.models import Listing, Photo
from app.schemas.photo import (
    PhotoConfirm,
    PhotoRead,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.photo_tasks import generate_thumbnail
from app.services.storage import (
    build_object_key,
    create_upload_url,
    delete_object,
    get_object_info,
    public_url,
)

router = APIRouter(tags=["photos"])

UPLOAD_URL_TTL = 600
MAX_PHOTOS_PER_LISTING = 8


def to_read(photo: Photo) -> PhotoRead:
    return PhotoRead(
        id=photo.id,
        url=public_url(photo.object_key),
        thumb_url=public_url(photo.thumb_key) if photo.thumb_key else None,
        is_primary=photo.is_primary,
        sort_order=photo.sort_order,
        created_at=photo.created_at,
    )


async def _get_own_listing(listing_id: int, user_id: int, session) -> Listing:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if listing.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Это не ваше объявление")
    return listing


@router.post("/listings/{listing_id}/photos/upload-url", response_model=UploadUrlResponse)
async def request_upload_url(
    listing_id: int, data: UploadUrlRequest, user: CurrentUser, session: SessionDep
) -> UploadUrlResponse:
    await _get_own_listing(listing_id, user.id, session)

    count = await session.scalar(
        select(func.count()).select_from(Photo).where(Photo.listing_id == listing_id)
    )
    if count and count >= MAX_PHOTOS_PER_LISTING:
        raise HTTPException(
            status_code=409,
            detail=f"Не больше {MAX_PHOTOS_PER_LISTING} фотографий на объявление",
        )

    object_key = build_object_key(listing_id, data.content_type)
    upload_url = create_upload_url(object_key, data.content_type, UPLOAD_URL_TTL)

    return UploadUrlResponse(
        upload_url=upload_url, object_key=object_key, expires_in=UPLOAD_URL_TTL
    )


@router.post(
    "/listings/{listing_id}/photos",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_photo(
    listing_id: int,
    data: PhotoConfirm,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
) -> PhotoRead:
    await _get_own_listing(listing_id, user.id, session)

    if not data.object_key.startswith(f"listings/{listing_id}/"):
        raise HTTPException(status_code=400, detail="Ключ не принадлежит объявлению")

    info = await asyncio.to_thread(get_object_info, data.object_key)
    if info is None:
        raise HTTPException(status_code=404, detail="Файл не найден в хранилище")

    count = await session.scalar(
        select(func.count()).select_from(Photo).where(Photo.listing_id == listing_id)
    )

    photo = Photo(
        listing_id=listing_id,
        object_key=data.object_key,
        content_type=info["content_type"],
        size_bytes=info["size"],
        is_primary=not count,
        sort_order=count or 0,
    )
    session.add(photo)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Эта фотография уже добавлена") from None

    await session.refresh(photo)
    background.add_task(generate_thumbnail, photo.id, photo.object_key)
    return to_read(photo)


@router.get("/listings/{listing_id}/photos", response_model=list[PhotoRead])
async def list_photos(listing_id: int, session: SessionDep) -> list[PhotoRead]:
    photos = await session.scalars(
        select(Photo).where(Photo.listing_id == listing_id).order_by(Photo.sort_order)
    )
    return [to_read(p) for p in photos]


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: int, user: CurrentUser, session: SessionDep) -> None:
    photo = await session.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Фотография не найдена")

    await _get_own_listing(photo.listing_id, user.id, session)

    keys = [photo.object_key]
    if photo.thumb_key:
        keys.append(photo.thumb_key)

    await session.delete(photo)
    await session.commit()

    for key in keys:
        await asyncio.to_thread(delete_object, key)
