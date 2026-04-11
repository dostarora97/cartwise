from httpx import AsyncClient

from app.models.user import User


async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_users_requires_no_auth(client: AsyncClient, test_user: User):
    response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["email"] == "test@example.com"


async def test_get_user(client: AsyncClient, test_user: User):
    response = await client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"


async def test_update_own_profile(client: AsyncClient, test_user: User, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/users/{test_user.id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
