from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import OptionalUser

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
