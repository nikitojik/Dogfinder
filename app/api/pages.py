from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import OptionalUser, SessionDep
from app.models import Listing

router = APIRouter(include_in_schema=False)


def render(request: Request, name: str, user, **context) -> HTMLResponse:
    from app.main import templates

    return templates.TemplateResponse(request=request, name=name, context={"user": user, **context})


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: OptionalUser):
    return render(request, "index.html", user)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: OptionalUser):
    if user is not None:
        return RedirectResponse("/", status_code=302)
    return render(request, "login.html", user)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: OptionalUser):
    if user is not None:
        return RedirectResponse("/", status_code=302)
    return render(request, "register.html", user)


@router.get("/listings/new", response_class=HTMLResponse)
async def listing_new_page(request: Request, user: OptionalUser):
    if user is None:
        return RedirectResponse("/login", status_code=302)
    return render(request, "listing_new.html", user)


@router.get("/listings/{listing_id}", response_class=HTMLResponse)
async def listing_page(listing_id: int, request: Request, user: OptionalUser, session: SessionDep):
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

    return render(request, "listing.html", user, listing=listing)


@router.get("/my", response_class=HTMLResponse)
async def my_listings_page(request: Request, user: OptionalUser):
    if user is None:
        return RedirectResponse("/login", status_code=302)
    return render(request, "my_listings.html", user)
