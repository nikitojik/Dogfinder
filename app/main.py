from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.listings import router as listings_router
from app.api.pages import router as pages_router
from app.api.photos import router as photos_router
from app.api.responses import router as responses_router
from app.config import settings
from app.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="DogFinder",
    description="Сервис поиска пропавших собак",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(listings_router)
app.include_router(responses_router)
app.include_router(photos_router)
app.include_router(pages_router)
BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    async with engine.connect() as conn:
        postgis = await conn.scalar(text("SELECT postgis_version()"))
        pgvector = await conn.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
    return {
        "status": "ok",
        "postgis": postgis or "not installed",
        "pgvector": pgvector or "not installed",
    }
