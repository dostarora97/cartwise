"""Unit tests for menu item endpoints."""

import uuid

from httpx import AsyncClient


async def test_create_menu_item(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/menu-items/",
        json={
            "name": "Chicken Curry",
            "body": "## Recipe\nCook chicken with spices.\n\n## Ingredients\nchicken, onion, spices",
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
        json={"name": "Salad", "body": "Chop veggies.\n\ncucumber, tomato"},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/menu-items/")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_menu_items_filter_by_status(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "Active", "body": "active item body"},
        headers=auth_headers,
    )
    resp2 = await client.post(
        "/api/v1/menu-items/",
        json={"name": "ToArchive", "body": "to archive body"},
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
        json={"name": "Mine", "body": "my item body"},
        headers=auth_headers,
    )
    response = await client.get(f"/api/v1/menu-items/?created_by={test_user.id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1


async def test_get_menu_item_by_id(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "GetMe", "body": "get me body"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]
    response = await client.get(f"/api/v1/menu-items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetMe"


async def test_get_menu_item_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/menu-items/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_menu_item(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Before", "body": "old body"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/menu-items/{item_id}",
        json={"name": "After", "body": "new body"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "After"
    assert response.json()["body"] == "new body"


async def test_update_menu_item_partial(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Original", "body": "original body"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/menu-items/{item_id}",
        json={"name": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["body"] == "original body"  # unchanged


async def test_update_menu_item_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/menu-items/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_archive_menu_item(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Soup", "body": "boil veggies"},
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


async def test_unarchive_menu_item(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Soup", "body": "boil veggies"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    await client.patch(f"/api/v1/menu-items/{item_id}/archive", headers=auth_headers)
    response = await client.patch(f"/api/v1/menu-items/{item_id}/unarchive", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "active"


async def test_unarchive_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/menu-items/{uuid.uuid4()}/unarchive", headers=auth_headers
    )
    assert response.status_code == 404
