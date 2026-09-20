from httpx import AsyncClient

from tests.helpers import auth

BASE = {
    "kind": "found",
    "title": "Найдена собака",
    "happened_at": "2026-09-01T12:00:00Z",
}

CENTER_LAT, CENTER_LON = 61.0667, 42.1


async def create_at(client: AsyncClient, token: str, lat: float, lon: float, title: str):
    await client.post(
        "/api/listings",
        json={**BASE, "title": title, "lat": lat, "lon": lon},
        headers=auth(token),
    )


async def test_radius_filters_by_distance(client: AsyncClient, user_token: str):
    await create_at(client, user_token, CENTER_LAT, CENTER_LON, "В центре")
    await create_at(client, user_token, CENTER_LAT + 0.009, CENTER_LON, "Километр")
    await create_at(client, user_token, CENTER_LAT + 0.45, CENTER_LON, "Полсотни км")

    response = await client.get(f"/api/listings?lat={CENTER_LAT}&lon={CENTER_LON}&radius_km=5")

    assert response.json()["total"] == 2


async def test_distance_is_returned_in_meters(client: AsyncClient, user_token: str):
    await create_at(client, user_token, CENTER_LAT + 0.009, CENTER_LON, "Километр")

    response = await client.get(f"/api/listings?lat={CENTER_LAT}&lon={CENTER_LON}&radius_km=5")

    distance = response.json()["items"][0]["distance_m"]
    assert 900 < distance < 1100


async def test_sort_by_distance(client: AsyncClient, user_token: str):
    await create_at(client, user_token, CENTER_LAT + 0.02, CENTER_LON, "Дальше")
    await create_at(client, user_token, CENTER_LAT + 0.005, CENTER_LON, "Ближе")

    response = await client.get(
        f"/api/listings?lat={CENTER_LAT}&lon={CENTER_LON}&radius_km=10&sort=distance"
    )

    items = response.json()["items"]
    assert items[0]["title"] == "Ближе"


async def test_single_coordinate_is_rejected(client: AsyncClient):
    response = await client.get(f"/api/listings?lat={CENTER_LAT}")

    assert response.status_code == 400


async def test_radius_without_point_is_rejected(client: AsyncClient):
    response = await client.get("/api/listings?radius_km=5")

    assert response.status_code == 400
