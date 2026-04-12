"""Unit tests for meal plan endpoints."""

import uuid

from httpx import AsyncClient


async def _create_item(client: AsyncClient, auth_headers: dict, name: str = "Item") -> str:
    resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": name, "recipe": "r", "ingredients": "i"},
        headers=auth_headers,
    )
    return resp.json()["id"]


async def test_get_empty_meal_plan(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/meal-plans/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_set_meal_plan(client: AsyncClient, auth_headers: dict):
    id1 = await _create_item(client, auth_headers, "A")
    id2 = await _create_item(client, auth_headers, "B")

    response = await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [id1, id2]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


async def test_set_meal_plan_nonexistent_item(client: AsyncClient, auth_headers: dict):
    response = await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [str(uuid.uuid4())]},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_set_meal_plan_replaces_previous(client: AsyncClient, auth_headers: dict):
    id1 = await _create_item(client, auth_headers, "Old")
    id2 = await _create_item(client, auth_headers, "New")

    await client.put("/api/v1/meal-plans/me", json={"menu_item_ids": [id1]}, headers=auth_headers)
    response = await client.put(
        "/api/v1/meal-plans/me", json={"menu_item_ids": [id2]}, headers=auth_headers
    )
    item_ids = [i["menu_item_id"] for i in response.json()["items"]]
    assert id2 in item_ids
    assert id1 not in item_ids


async def test_add_item_to_plan(client: AsyncClient, auth_headers: dict):
    item_id = await _create_item(client, auth_headers)

    response = await client.post(
        "/api/v1/meal-plans/me/items",
        json={"menu_item_id": item_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


async def test_add_item_idempotent(client: AsyncClient, auth_headers: dict):
    item_id = await _create_item(client, auth_headers)

    await client.post(
        "/api/v1/meal-plans/me/items", json={"menu_item_id": item_id}, headers=auth_headers
    )
    response = await client.post(
        "/api/v1/meal-plans/me/items", json={"menu_item_id": item_id}, headers=auth_headers
    )
    assert len(response.json()["items"]) == 1  # not duplicated


async def test_add_nonexistent_item(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/meal-plans/me/items",
        json={"menu_item_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_remove_item_from_plan(client: AsyncClient, auth_headers: dict):
    id1 = await _create_item(client, auth_headers, "Keep")
    id2 = await _create_item(client, auth_headers, "Remove")

    await client.put(
        "/api/v1/meal-plans/me", json={"menu_item_ids": [id1, id2]}, headers=auth_headers
    )
    response = await client.delete(f"/api/v1/meal-plans/me/items/{id2}", headers=auth_headers)
    assert response.status_code == 200
    item_ids = [i["menu_item_id"] for i in response.json()["items"]]
    assert id1 in item_ids
    assert id2 not in item_ids


async def test_add_and_remove_meal_plan_item(client: AsyncClient, auth_headers: dict):
    """Original test — add two items, remove one."""
    id1 = await _create_item(client, auth_headers, "A")
    id2 = await _create_item(client, auth_headers, "B")

    await client.post(
        "/api/v1/meal-plans/me/items", json={"menu_item_id": id1}, headers=auth_headers
    )
    resp = await client.post(
        "/api/v1/meal-plans/me/items", json={"menu_item_id": id2}, headers=auth_headers
    )
    assert len(resp.json()["items"]) == 2

    resp = await client.delete(f"/api/v1/meal-plans/me/items/{id1}", headers=auth_headers)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["menu_item_id"] == id2
