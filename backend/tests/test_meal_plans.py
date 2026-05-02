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


async def _archive_item(client: AsyncClient, auth_headers: dict, item_id: str):
    await client.patch(f"/api/v1/menu-items/{item_id}/archive", headers=auth_headers)


async def test_get_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/meal-plans")
    assert response.status_code == 401


async def test_put_requires_auth(client: AsyncClient):
    response = await client.put("/api/v1/meal-plans", json={"menu_item_ids": []})
    assert response.status_code == 401


async def test_get_empty_meal_plan(client: AsyncClient, auth_headers: dict, test_user):
    response = await client.get("/api/v1/meal-plans", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert "id" in data
    assert "updated_at" in data


async def test_response_has_no_user_id(client: AsyncClient, auth_headers: dict, test_user):
    response = await client.get("/api/v1/meal-plans", headers=auth_headers)
    assert "user_id" not in response.json()


async def test_set_meal_plan(client: AsyncClient, auth_headers: dict, test_user):
    id1 = await _create_item(client, auth_headers, "A")
    id2 = await _create_item(client, auth_headers, "B")

    response = await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [id1, id2]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["rank"] == 0
    assert items[0]["menu_item"]["id"] == id1
    assert items[0]["menu_item"]["name"] == "A"
    assert items[0]["menu_item"]["status"] == "active"
    assert items[1]["rank"] == 1
    assert items[1]["menu_item"]["id"] == id2
    assert items[1]["menu_item"]["name"] == "B"


async def test_set_meal_plan_nonexistent_item(client: AsyncClient, auth_headers: dict, test_user):
    response = await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [str(uuid.uuid4())]},
        headers=auth_headers,
    )
    assert response.status_code == 400


async def test_set_meal_plan_replaces_previous(client: AsyncClient, auth_headers: dict, test_user):
    id1 = await _create_item(client, auth_headers, "Old")
    id2 = await _create_item(client, auth_headers, "New")

    await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [id1]},
        headers=auth_headers,
    )
    response = await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [id2]},
        headers=auth_headers,
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["menu_item"]["id"] == id2
    assert items[0]["rank"] == 0


async def test_put_archived_item_rejected(client: AsyncClient, auth_headers: dict, test_user):
    item_id = await _create_item(client, auth_headers, "Archivable")
    await _archive_item(client, auth_headers, item_id)

    response = await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [item_id]},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "archived" in response.json()["detail"].lower()


async def test_put_empty_array_clears_plan(client: AsyncClient, auth_headers: dict, test_user):
    item_id = await _create_item(client, auth_headers, "Temp")

    await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [item_id]},
        headers=auth_headers,
    )
    response = await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_meal_plan_order_preserved(client: AsyncClient, auth_headers: dict, test_user):
    """Set plan in specific order, verify order is preserved on GET."""
    id1 = await _create_item(client, auth_headers, "First")
    id2 = await _create_item(client, auth_headers, "Second")
    id3 = await _create_item(client, auth_headers, "Third")

    await client.put(
        "/api/v1/meal-plans",
        json={"menu_item_ids": [id3, id1, id2]},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/meal-plans", headers=auth_headers)
    items = response.json()["items"]
    assert items[0]["menu_item"]["id"] == id3
    assert items[0]["rank"] == 0
    assert items[1]["menu_item"]["id"] == id1
    assert items[1]["rank"] == 1
    assert items[2]["menu_item"]["id"] == id2
    assert items[2]["rank"] == 2
