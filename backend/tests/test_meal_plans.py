"""Unit tests for meal plan endpoints."""

import uuid

from httpx import AsyncClient


async def _create_item(client: AsyncClient, auth_headers: dict, name: str = "Item") -> str:
    resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": name, "body": "test body"},
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
    items = response.json()["items"]
    assert len(items) == 2
    # Verify enriched nested response
    assert items[0]["rank"] == 0
    assert items[0]["menu_item"]["id"] == id1
    assert items[0]["menu_item"]["name"] == "A"
    assert items[0]["menu_item"]["status"] == "active"
    assert items[1]["rank"] == 1
    assert items[1]["menu_item"]["id"] == id2
    assert items[1]["menu_item"]["name"] == "B"


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
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["menu_item"]["id"] == id2
    assert items[0]["rank"] == 0


async def test_add_item_to_plan(client: AsyncClient, auth_headers: dict):
    item_id = await _create_item(client, auth_headers)

    response = await client.post(
        "/api/v1/meal-plans/me/items",
        json={"menu_item_id": item_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["rank"] == 0


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
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["menu_item"]["id"] == id1


async def test_add_and_remove_meal_plan_item(client: AsyncClient, auth_headers: dict):
    """Add two items, remove one."""
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
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["menu_item"]["id"] == id2


async def test_meal_plan_order_preserved(client: AsyncClient, auth_headers: dict):
    """Set plan in specific order, verify order is preserved on GET."""
    id1 = await _create_item(client, auth_headers, "First")
    id2 = await _create_item(client, auth_headers, "Second")
    id3 = await _create_item(client, auth_headers, "Third")

    # Set in reverse alphabetical order
    await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [id3, id1, id2]},
        headers=auth_headers,
    )

    # Get and verify order matches
    response = await client.get("/api/v1/meal-plans/me", headers=auth_headers)
    items = response.json()["items"]
    assert items[0]["menu_item"]["id"] == id3
    assert items[0]["rank"] == 0
    assert items[1]["menu_item"]["id"] == id1
    assert items[1]["rank"] == 1
    assert items[2]["menu_item"]["id"] == id2
    assert items[2]["rank"] == 2


async def test_add_item_appends_at_end(client: AsyncClient, auth_headers: dict):
    """Adding an item puts it after existing items."""
    id1 = await _create_item(client, auth_headers, "First")
    id2 = await _create_item(client, auth_headers, "Second")
    id3 = await _create_item(client, auth_headers, "Third")

    await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [id1, id2]},
        headers=auth_headers,
    )
    response = await client.post(
        "/api/v1/meal-plans/me/items",
        json={"menu_item_id": id3},
        headers=auth_headers,
    )
    items = response.json()["items"]
    assert len(items) == 3
    assert items[2]["menu_item"]["id"] == id3
    assert items[2]["rank"] == 2
