"""Tests for DELETE /auth/me (account deletion) and POST /auth/dev-login."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import User


async def test_delete_account_success(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """DELETE /auth/me with action='delete' removes user and associated data."""
    with (
        patch("app.routes.auth.delete_secret", new_callable=AsyncMock) as mock_del_secret,
        patch("app.routes.auth.delete_order_files"),
    ):
        resp = await client.request(
            "DELETE",
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"action": "delete"},
        )

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Account deleted"
    mock_del_secret.assert_called_once()

    # Verify user no longer in DB
    result = await session.execute(select(User).where(User.id == test_user.id))
    assert result.scalar_one_or_none() is None


async def test_delete_account_wrong_action(client: AsyncClient, auth_headers: dict, test_user):
    """DELETE /auth/me with wrong action returns 400."""
    resp = await client.request(
        "DELETE",
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"action": "remove"},
    )
    assert resp.status_code == 400
    assert "Must confirm" in resp.json()["detail"]


async def test_delete_account_no_auth(client: AsyncClient):
    """DELETE /auth/me without auth returns 401/403."""
    resp = await client.request("DELETE", "/api/v1/auth/me", json={"action": "delete"})
    assert resp.status_code in (401, 403)


async def test_delete_account_with_orders(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """DELETE /auth/me also deletes storage files for user's orders."""
    order = Order(paid_by=test_user.id, status="draft")
    session.add(order)
    await session.commit()
    await session.refresh(order)

    with (
        patch("app.routes.auth.delete_secret", new_callable=AsyncMock),
        patch("app.routes.auth.delete_order_files") as mock_del_files,
    ):
        resp = await client.request(
            "DELETE",
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"action": "delete"},
        )

    assert resp.status_code == 200
    mock_del_files.assert_called_once_with(order.id)


# --- Dev login ---


async def test_dev_login_creates_user(client: AsyncClient, session: AsyncSession, monkeypatch):
    """POST /auth/dev-login creates user and returns JWT when DEBUG=true."""
    monkeypatch.setattr("app.routes.auth.settings", _DebugSettings(debug=True))

    resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "dev@test.com", "name": "Dev User"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["user"]["email"] == "dev@test.com"
    assert data["user"]["name"] == "Dev User"


async def test_dev_login_existing_user(
    client: AsyncClient, test_user, session: AsyncSession, monkeypatch
):
    """POST /auth/dev-login returns existing user if email matches."""
    monkeypatch.setattr("app.routes.auth.settings", _DebugSettings(debug=True))

    resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": test_user.email, "name": "Ignored Name"},
    )

    assert resp.status_code == 200
    assert resp.json()["user"]["id"] == str(test_user.id)


async def test_dev_login_disabled_in_production(client: AsyncClient, monkeypatch):
    """POST /auth/dev-login returns 404 when DEBUG=false."""
    monkeypatch.setattr("app.routes.auth.settings", _DebugSettings(debug=False))

    resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "hack@test.com", "name": "Hacker"},
    )

    assert resp.status_code == 404


class _DebugSettings:
    """Minimal settings stub for dev-login tests."""

    SESSION_SECRET_KEY = "test-secret-key-for-signing"

    def __init__(self, debug=False):
        self._debug = debug

    def get(self, key, default=None):
        if key == "DEBUG":
            return self._debug
        return default
