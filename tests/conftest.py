import asyncio
import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://dogfinder:dogfinder@localhost:5432/dogfinder_test"

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    subprocess.run(
        ["alembic", "downgrade", "base"],
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
        capture_output=True,
    )
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables():
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as s:
        yield s


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def user_token(client: AsyncClient) -> str:
    await client.post(
        "/api/auth/register",
        json={
            "email": "alice@example.com",
            "password": "password123",
            "name": "Алиса",
            "phone": "+79001112233",
        },
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def other_token(client: AsyncClient) -> str:
    await client.post(
        "/api/auth/register",
        json={
            "email": "bob@example.com",
            "password": "password123",
            "name": "Боб",
            "phone": "+79004445566",
        },
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    return response.json()["access_token"]
