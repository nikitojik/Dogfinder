from httpx import AsyncClient

from tests.helpers import auth

VALID_USER = {
    "email": "new@example.com",
    "password": "password123",
    "name": "Новый",
    "phone": "+79001234567",
}


async def test_register_returns_user_without_password(client: AsyncClient):
    response = await client.post("/api/auth/register", json=VALID_USER)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_USER["email"]
    assert "hashed_password" not in body
    assert "password" not in body


async def test_register_rejects_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json=VALID_USER)
    response = await client.post("/api/auth/register", json=VALID_USER)

    assert response.status_code == 409


async def test_register_rejects_short_password(client: AsyncClient):
    response = await client.post("/api/auth/register", json={**VALID_USER, "password": "123"})

    assert response.status_code == 422


async def test_login_sets_cookie(client: AsyncClient):
    await client.post("/api/auth/register", json=VALID_USER)
    response = await client.post(
        "/api/auth/login",
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )

    assert response.status_code == 200
    assert "access_token" in response.cookies


async def test_login_rejects_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json=VALID_USER)
    response = await client.post(
        "/api/auth/login",
        json={"email": VALID_USER["email"], "password": "wrongpassword"},
    )

    assert response.status_code == 401


async def test_me_requires_token(client: AsyncClient):
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


async def test_me_rejects_broken_token(client: AsyncClient):
    response = await client.get("/api/auth/me", headers=auth("not.a.token"))

    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, user_token: str):
    response = await client.get("/api/auth/me", headers=auth(user_token))

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
