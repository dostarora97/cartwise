"""Unit tests for user endpoints."""

import uuid

from httpx import AsyncClient

from app.models.user import User


async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_users(client: AsyncClient, test_user: User):
    response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "test@example.com"


async def test_get_user(client: AsyncClient, test_user: User):
    response = await client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"


async def test_get_user_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_update_own_profile(client: AsyncClient, test_user: User, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/users/{test_user.id}",
        json={"name": "Updated Name", "phone": "+911234567890"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["phone"] == "+911234567890"


async def test_update_other_user_forbidden(
    client: AsyncClient, test_user: User, auth_headers: dict
):
    other_id = uuid.uuid4()  # doesn't matter — auth check happens first
    response = await client.patch(
        f"/api/v1/users/{other_id}",
        json={"name": "Hacked"},
        headers=auth_headers,
    )
    assert response.status_code == 403


async def test_update_empty_body_is_noop(client: AsyncClient, test_user: User, auth_headers: dict):
    response = await client.patch(
        f"/api/v1/users/{test_user.id}",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"  # unchanged
