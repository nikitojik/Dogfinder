from httpx import AsyncClient

from tests.helpers import auth

LISTING = {
    "kind": "lost",
    "title": "Пропал рыжий пёс",
    "happened_at": "2026-09-01T12:00:00Z",
    "breed": "Корги",
    "color": "рыжий",
    "size": "medium",
    "lat": 61.0667,
    "lon": 42.1,
}


async def create(client: AsyncClient, token: str, **overrides) -> dict:
    response = await client.post(
        "/api/listings", json={**LISTING, **overrides}, headers=auth(token)
    )
    return response.json()


async def test_create_requires_auth(client: AsyncClient):
    response = await client.post("/api/listings", json=LISTING)

    assert response.status_code == 401


async def test_create_returns_coordinates(client: AsyncClient, user_token: str):
    response = await client.post("/api/listings", json=LISTING, headers=auth(user_token))

    assert response.status_code == 201
    body = response.json()
    assert round(body["lat"], 4) == 61.0667
    assert round(body["lon"], 4) == 42.1


async def test_create_rejects_invalid_latitude(client: AsyncClient, user_token: str):
    response = await client.post(
        "/api/listings", json={**LISTING, "lat": 200}, headers=auth(user_token)
    )

    assert response.status_code == 422


async def test_listing_without_coordinates_is_allowed(client: AsyncClient, user_token: str):
    payload = {k: v for k, v in LISTING.items() if k not in {"lat", "lon"}}
    response = await client.post("/api/listings", json=payload, headers=auth(user_token))

    assert response.status_code == 201
    assert response.json()["lat"] is None


async def test_owner_can_update(client: AsyncClient, user_token: str):
    listing = await create(client, user_token)

    response = await client.patch(
        f"/api/listings/{listing['id']}",
        json={"title": "Новый заголовок"},
        headers=auth(user_token),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Новый заголовок"


async def test_stranger_cannot_update(client: AsyncClient, user_token: str, other_token: str):
    listing = await create(client, user_token)

    response = await client.patch(
        f"/api/listings/{listing['id']}",
        json={"title": "Взлом"},
        headers=auth(other_token),
    )

    assert response.status_code == 403


async def test_patch_keeps_untouched_fields(client: AsyncClient, user_token: str):
    listing = await create(client, user_token, description="Описание на месте")

    await client.patch(
        f"/api/listings/{listing['id']}",
        json={"title": "Другой заголовок"},
        headers=auth(user_token),
    )
    response = await client.get(f"/api/listings/{listing['id']}")

    assert response.json()["description"] == "Описание на месте"


async def test_delete_archives_listing(client: AsyncClient, user_token: str):
    listing = await create(client, user_token)

    response = await client.delete(f"/api/listings/{listing['id']}", headers=auth(user_token))
    assert response.status_code == 204

    feed = await client.get("/api/listings")
    assert listing["id"] not in [item["id"] for item in feed.json()["items"]]

    archived = await client.get("/api/listings?status=archived")
    assert listing["id"] in [item["id"] for item in archived.json()["items"]]


async def test_filter_by_kind(client: AsyncClient, user_token: str):
    await create(client, user_token, kind="lost")
    await create(client, user_token, kind="found", title="Найден пёс")

    response = await client.get("/api/listings?kind=found")

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["kind"] == "found"


async def test_filter_by_breed_is_partial(client: AsyncClient, user_token: str):
    await create(client, user_token, breed="Немецкая овчарка")
    await create(client, user_token, breed="Корги", title="Второй")

    response = await client.get("/api/listings?breed=овчар")

    assert response.json()["total"] == 1


async def test_pagination(client: AsyncClient, user_token: str):
    for index in range(5):
        await create(client, user_token, title=f"Объявление {index}")

    first = await client.get("/api/listings?limit=2&offset=0")
    second = await client.get("/api/listings?limit=2&offset=2")

    assert first.json()["total"] == 5
    assert len(first.json()["items"]) == 2
    first_ids = {item["id"] for item in first.json()["items"]}
    second_ids = {item["id"] for item in second.json()["items"]}
    assert not first_ids & second_ids
