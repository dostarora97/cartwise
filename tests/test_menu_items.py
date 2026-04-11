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
    # Create one first
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "Salad", "recipe": "Chop veggies.", "ingredients": "cucumber, tomato"},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/menu-items/")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_fork_menu_item(client: AsyncClient, auth_headers: dict):
    # Create original
    create_resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Pasta", "recipe": "Boil pasta.", "ingredients": "pasta, sauce"},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]

    # Fork it
    fork_resp = await client.post(
        f"/api/v1/menu-items/{item_id}/fork",
        headers=auth_headers,
    )
    assert fork_resp.status_code == 201
    forked = fork_resp.json()
    assert forked["name"] == "Pasta"
    assert forked["id"] != item_id


async def test_archive_menu_item(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Soup", "recipe": "Boil.", "ingredients": "veggies"},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]

    archive_resp = await client.patch(
        f"/api/v1/menu-items/{item_id}/archive",
        headers=auth_headers,
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"
