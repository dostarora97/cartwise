from httpx import AsyncClient


async def test_get_empty_meal_plan(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/meal-plans/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


async def test_set_meal_plan(client: AsyncClient, auth_headers: dict):
    # Create a menu item first
    item_resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Rice", "recipe": "Boil rice.", "ingredients": "rice"},
        headers=auth_headers,
    )
    item_id = item_resp.json()["id"]

    # Set meal plan
    response = await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [item_id]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["menu_item_id"] == item_id


async def test_add_and_remove_meal_plan_item(client: AsyncClient, auth_headers: dict):
    # Create two menu items
    item1 = await client.post(
        "/api/v1/menu-items/",
        json={"name": "A", "recipe": "a", "ingredients": "a"},
        headers=auth_headers,
    )
    item2 = await client.post(
        "/api/v1/menu-items/",
        json={"name": "B", "recipe": "b", "ingredients": "b"},
        headers=auth_headers,
    )
    id1 = item1.json()["id"]
    id2 = item2.json()["id"]

    # Add first
    await client.post(
        "/api/v1/meal-plans/me/items",
        json={"menu_item_id": id1},
        headers=auth_headers,
    )

    # Add second
    resp = await client.post(
        "/api/v1/meal-plans/me/items",
        json={"menu_item_id": id2},
        headers=auth_headers,
    )
    assert len(resp.json()["items"]) == 2

    # Remove first
    resp = await client.delete(
        f"/api/v1/meal-plans/me/items/{id1}",
        headers=auth_headers,
    )
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["menu_item_id"] == id2
