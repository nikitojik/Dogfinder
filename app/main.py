from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

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
