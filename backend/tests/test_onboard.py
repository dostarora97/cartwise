"""Unit tests for auth endpoints: /auth/me, /auth/onboard."""

from httpx import AsyncClient

from app.auth.jwt import create_test_token


async def test_auth_me_returns_user(client: AsyncClient, auth_headers: dict, test_user):
    """GET /auth/me returns the authenticated user."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email
    assert response.json()["name"] == test_user.name


async def test_auth_me_no_token(client: AsyncClient):
    """GET /auth/me without token returns 401/403."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


async def test_auth_me_before_onboard(client: AsyncClient):
    """GET /auth/me with valid JWT but no user in DB returns 404."""
    token = create_test_token("not-onboarded-oauth-id", "new@test.com")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


async def test_onboard_creates_user(client: AsyncClient):
    """POST /auth/onboard creates a new user."""
    token = create_test_token("fresh-oauth-id", "fresh@test.com")
    response = await client.post(
        "/api/v1/auth/onboard",
        json={"name": "Fresh User", "phone": "9876543210", "splitwise_user_id": 12345},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Fresh User"
    assert data["phone"] == "9876543210"
    assert data["splitwise_user_id"] == 12345
    assert data["email"] == "fresh@test.com"


async def test_onboard_then_auth_me(client: AsyncClient):
    """After onboarding, GET /auth/me works."""
    token = create_test_token("onboard-then-me", "onboard@test.com")

    # Before onboard: 404
    resp1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 404

    # Onboard
    await client.post(
        "/api/v1/auth/onboard",
        json={"name": "Onboarded", "phone": "1234567890", "splitwise_user_id": 99},
        headers={"Authorization": f"Bearer {token}"},
    )

    # After onboard: 200
    resp2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Onboarded"


async def test_onboard_duplicate(client: AsyncClient):
    """Onboarding twice with the same JWT returns 409."""
    token = create_test_token("dup-oauth-id", "dup@test.com")

    resp1 = await client.post(
        "/api/v1/auth/onboard",
        json={"name": "First", "phone": "1111111111", "splitwise_user_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/api/v1/auth/onboard",
        json={"name": "Second", "phone": "2222222222", "splitwise_user_id": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 409


async def test_onboard_no_token(client: AsyncClient):
    """POST /auth/onboard without token returns 401/403."""
    response = await client.post(
        "/api/v1/auth/onboard",
        json={"name": "No Token", "phone": "0000000000", "splitwise_user_id": 1},
    )
    assert response.status_code in (401, 403)
