"""Tests for POST /auth/swiggy/disconnect endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def test_swiggy_disconnect_success(
    client: AsyncClient, session: AsyncSession, auth_headers: dict, test_user: User
):
    """Clears swiggy fields and deletes vault secret."""
    # Set up user as connected
    test_user.swiggy_user_id = "swiggy-123"
    test_user.swiggy_connected_at = datetime.now(UTC)
    await session.commit()

    with patch("app.routes.auth.delete_secret", new_callable=AsyncMock) as mock_delete:
        resp = await client.post("/api/v1/auth/swiggy/disconnect", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    mock_delete.assert_called_once_with(session, f"swiggy_token:{test_user.id}")

    # Verify user fields cleared
    await session.refresh(test_user)
    assert test_user.swiggy_user_id is None
    assert test_user.swiggy_connected_at is None


async def test_swiggy_disconnect_already_disconnected(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    """Succeeds even when user is not currently connected."""
    with patch("app.routes.auth.delete_secret", new_callable=AsyncMock):
        resp = await client.post("/api/v1/auth/swiggy/disconnect", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


async def test_swiggy_disconnect_no_auth(client: AsyncClient):
    """Returns 401 without auth headers."""
    resp = await client.post("/api/v1/auth/swiggy/disconnect")
    assert resp.status_code in (401, 403)
