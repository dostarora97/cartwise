"""Unit tests for menu item endpoints."""

import uuid

from httpx import AsyncClient


async def test_create_menu_item(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/menu-items/",
        json={
            "name": "Chicken Curry",
            "recipe": "## Chicken Curry\n\nCook chicken with spices.",
            "ingredients": "chicken, onion, spices",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Chicken Curry"
    assert data["status"] == "active"


async def test_list_menu_items(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "Salad", "recipe": "Chop veggies.", "ingredients": "cucumber, tomato"},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/menu-items/")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_menu_items_filter_by_status(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "Active", "recipe": "r", "ingredients": "i"},
        headers=auth_headers,
    )
    resp2 = await client.post(
        "/api/v1/menu-items/",
        json={"name": "ToArchive", "recipe": "r", "ingredients": "i"},
        headers=auth_headers,
    )
    await client.patch(f"/api/v1/menu-items/{resp2.json()['id']}/archive", headers=auth_headers)

    active = await client.get("/api/v1/menu-items/?status=active")
    assert all(i["status"] == "active" for i in active.json())
    assert any(i["name"] == "Active" for i in active.json())

    archived = await client.get("/api/v1/menu-items/?status=archived")
    assert all(i["status"] == "archived" for i in archived.json())


async def test_list_menu_items_filter_by_creator(
    client: AsyncClient, auth_headers: dict, test_user
):
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "Mine", "recipe": "r", "ingredients": "i"},
        headers=auth_headers,
    )
    response = await client.get(f"/api/v1/menu-items/?created_by={test_user.id}")
    assert response.status_code == 200
    assert all(i["created_by"] == str(test_user.id) for i in response.json())


async def test_get_menu_item_by_id(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "GetMe", "recipe": "r", "ingredients": "i"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]
    response = await client.get(f"/api/v1/menu-items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetMe"


async def test_get_menu_item_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/menu-items/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_menu_item(client: AsyncClient, auth_headers: dict, test_user):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Before", "recipe": "old", "ingredients": "old"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/menu-items/{item_id}",
        json={"name": "After", "ingredients": "new"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "After"
    assert response.json()["ingredients"] == "new"
    assert response.json()["recipe"] == "old"  # unchanged
    assert response.json()["updated_by"] == str(test_user.id)


async def test_update_menu_item_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/menu-items/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_fork_menu_item(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Original", "recipe": "Boil.", "ingredients": "pasta, sauce"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    fork_resp = await client.post(f"/api/v1/menu-items/{item_id}/fork", headers=auth_headers)
    assert fork_resp.status_code == 201
    assert fork_resp.json()["name"] == "Original"
    assert fork_resp.json()["id"] != item_id


async def test_fork_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.post(f"/api/v1/menu-items/{uuid.uuid4()}/fork", headers=auth_headers)
    assert response.status_code == 404


async def test_archive_menu_item(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Soup", "recipe": "Boil.", "ingredients": "veggies"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    response = await client.patch(f"/api/v1/menu-items/{item_id}/archive", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


async def test_archive_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/menu-items/{uuid.uuid4()}/archive", headers=auth_headers
    )
    assert response.status_code == 404
