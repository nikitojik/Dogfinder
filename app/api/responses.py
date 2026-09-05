from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.models import Listing, Response
from app.schemas.response import ResponseCreate, ResponseRead, ResponseStatusUpdate

router = APIRouter(tags=["responses"])


@router.post(
    "/listings/{listing_id}/responses",
    response_model=ResponseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_response(
    listing_id: int, data: ResponseCreate, user: CurrentUser, session: SessionDep
) -> Response:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if listing.owner_id == user.id:
        raise HTTPException(status_code=400, detail="Нельзя откликнуться на собственное объявление")

    response = Response(
        listing_id=listing_id,
        author_id=user.id,
        message=data.message,
        contact_phone=data.contact_phone or user.phone,
    )
    session.add(response)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Вы уже откликнулись на это объявление"
        ) from None

    return await session.scalar(
        select(Response).where(Response.id == response.id).options(selectinload(Response.author))
    )


@router.get("/listings/{listing_id}/responses", response_model=list[ResponseRead])
async def list_responses(listing_id: int, user: CurrentUser, session: SessionDep) -> list[Response]:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Отклики видны только автору объявления")

    items = await session.scalars(
        select(Response)
        .where(Response.listing_id == listing_id)
        .options(selectinload(Response.author))
        .order_by(Response.created_at.desc())
    )
    return list(items)


@router.patch("/responses/{response_id}", response_model=ResponseRead)
async def update_response_status(
    response_id: int,
    data: ResponseStatusUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> Response:
    response = await session.scalar(
        select(Response)
        .where(Response.id == response_id)
        .options(selectinload(Response.author), selectinload(Response.listing))
    )
    if response is None:
        raise HTTPException(status_code=404, detail="Отклик не найден")
    if response.listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    response.status = data.status
    await session.commit()
    await session.refresh(response)
    return response
