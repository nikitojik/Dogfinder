from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import LocaleDep, OptionalUser, SessionDep
from app.core.i18n import gettext_for, normalize_locale
from app.core.templating import templates
from app.models import Listing

router = APIRouter(include_in_schema=False)


def render(request: Request, name: str, user, locale: str = "en", **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "user": user,
            "locale": locale,
            "_": gettext_for(locale),
            **context,
        },
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: OptionalUser, locale: LocaleDep):
    return render(request, "index.html", user, locale=locale)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: OptionalUser, locale: LocaleDep):
    if user is not None:
        return RedirectResponse("/", status_code=302)
    return render(request, "login.html", user, locale=locale)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: OptionalUser, locale: LocaleDep):
    if user is not None:
        return RedirectResponse("/", status_code=302)
    return render(request, "register.html", user, locale=locale)


@router.get("/feed", response_class=HTMLResponse)
async def feed_page(request: Request, user: OptionalUser, locale: LocaleDep):
    return render(request, "feed.html", user, locale=locale)


@router.get("/my", response_class=HTMLResponse)
async def my_listings_page(request: Request, user: OptionalUser, locale: LocaleDep):
    if user is None:
        return RedirectResponse("/login", status_code=302)
    return render(request, "my_listings.html", user, locale=locale)


@router.get("/lang/{code}")
async def set_language(code: str, request: Request, user: OptionalUser, session: SessionDep):
    target = normalize_locale(code)
    referer = request.headers.get("referer", "/")

    if user is not None and user.locale != target:
        user.locale = target
        await session.commit()

    response = RedirectResponse(referer, status_code=302)
    response.set_cookie("lang", target, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


@router.get("/listings/new", response_class=HTMLResponse)
async def listing_new_page(request: Request, user: OptionalUser, locale: LocaleDep):
    if user is None:
        return RedirectResponse("/login", status_code=302)
    return render(request, "listing_new.html", user, locale=locale)


@router.get("/listings/{listing_id}", response_class=HTMLResponse)
async def listing_page(
    listing_id: int,
    request: Request,
    user: OptionalUser,
    session: SessionDep,
    locale: LocaleDep,
):
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.owner), selectinload(Listing.photos))
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

    return render(request, "listing.html", user, locale=locale, listing=listing)
