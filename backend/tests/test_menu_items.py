"""Unit tests for menu item endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_test_token
from app.models.user import User


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


async def test_list_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/menu-items/")
    assert response.status_code in (401, 403)


async def test_list_menu_items(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "Salad", "body": "Chop veggies.\n\ncucumber, tomato"},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/menu-items/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_list_scoped_to_current_user(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Each user only sees their own items."""
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "MyItem", "body": "mine"},
        headers=auth_headers,
    )

    other_user = User(
        email="other_list@example.com",
        name="Other",
        oauth_provider="google",
        oauth_id="other-list-oauth",
    )
    session.add(other_user)
    await session.commit()
    other_token = create_test_token(other_user.oauth_id, other_user.email)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    await client.post(
        "/api/v1/menu-items/",
        json={"name": "TheirItem", "body": "theirs"},
        headers=other_headers,
    )

    my_items = await client.get("/api/v1/menu-items/", headers=auth_headers)
    assert all(i["name"] != "TheirItem" for i in my_items.json())
    assert any(i["name"] == "MyItem" for i in my_items.json())

    their_items = await client.get("/api/v1/menu-items/", headers=other_headers)
    assert all(i["name"] != "MyItem" for i in their_items.json())
    assert any(i["name"] == "TheirItem" for i in their_items.json())


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

    active = await client.get("/api/v1/menu-items/?status=active", headers=auth_headers)
    assert all(i["status"] == "active" for i in active.json())
    assert any(i["name"] == "Active" for i in active.json())

    archived = await client.get("/api/v1/menu-items/?status=archived", headers=auth_headers)
    assert all(i["status"] == "archived" for i in archived.json())


async def test_list_multiple_statuses(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/menu-items/",
        json={"name": "ActiveMulti", "body": "body"},
        headers=auth_headers,
    )
    resp2 = await client.post(
        "/api/v1/menu-items/",
        json={"name": "ArchivedMulti", "body": "body"},
        headers=auth_headers,
    )
    await client.patch(f"/api/v1/menu-items/{resp2.json()['id']}/archive", headers=auth_headers)

    both = await client.get("/api/v1/menu-items/?status=active,archived", headers=auth_headers)
    assert both.status_code == 200
    names = [i["name"] for i in both.json()]
    assert "ActiveMulti" in names
    assert "ArchivedMulti" in names


async def test_list_invalid_status(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/menu-items/?status=bogus", headers=auth_headers)
    assert response.status_code == 400


async def test_response_includes_created_by(client: AsyncClient, auth_headers: dict, test_user):
    resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": "WithCreator", "body": "body"},
        headers=auth_headers,
    )
    data = resp.json()
    assert data["created_by"] == str(test_user.id)
    assert data["updated_by"] == str(test_user.id)


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
    assert response.json()["body"] == "original body"


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


async def test_modify_other_users_item_returns_403(
    client: AsyncClient, auth_headers: dict, session: AsyncSession
):
    """Users cannot modify menu items they don't own — returns 403."""
    created = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Private", "body": "owner only"},
        headers=auth_headers,
    )
    item_id = created.json()["id"]

    other_user = User(
        email="other@example.com",
        name="Other",
        oauth_provider="google",
        oauth_id="other-oauth-id",
    )
    session.add(other_user)
    await session.commit()
    other_token = create_test_token(other_user.oauth_id, other_user.email)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert (
        await client.patch(
            f"/api/v1/menu-items/{item_id}", json={"name": "Hacked"}, headers=other_headers
        )
    ).status_code == 403

    assert (
        await client.patch(f"/api/v1/menu-items/{item_id}/archive", headers=other_headers)
    ).status_code == 403

    assert (
        await client.patch(f"/api/v1/menu-items/{item_id}/unarchive", headers=other_headers)
    ).status_code == 403
