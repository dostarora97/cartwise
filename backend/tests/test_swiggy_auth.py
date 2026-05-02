"""Tests for Swiggy auth token management."""

import base64
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ProblemDetailError
from app.services.swiggy.auth import _extract_exp, _refresh_token, get_valid_token


async def test_get_valid_token_no_token_raises(session: AsyncSession, test_user):
    """Raises ProblemDetailError when no token exists in vault."""
    with patch("app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=None):
        with pytest.raises(ProblemDetailError) as exc_info:
            await get_valid_token(session, str(test_user.id))
        assert exc_info.value.status == 422
        assert "swiggy" in exc_info.value.extras.get("provider", "")


async def test_get_valid_token_missing_access_token_raises(session: AsyncSession, test_user):
    """Raises ProblemDetailError when stored JSON has no access_token."""
    token_data = json.dumps({"refresh_token": "refresh-only", "expires_at": 999999999999})
    with (
        patch(
            "app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=token_data
        ),
        pytest.raises(ProblemDetailError),
    ):
        await get_valid_token(session, str(test_user.id))


async def test_get_valid_token_missing_refresh_token_raises(session: AsyncSession, test_user):
    """Raises ProblemDetailError when stored JSON has no refresh_token."""
    token_data = json.dumps({"access_token": "access-only", "expires_at": 999999999999})
    with (
        patch(
            "app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=token_data
        ),
        pytest.raises(ProblemDetailError),
    ):
        await get_valid_token(session, str(test_user.id))


async def test_get_valid_token_valid(session: AsyncSession, test_user):
    """Returns access_token directly when not expired."""
    token_data = json.dumps(
        {
            "access_token": "valid-token",
            "refresh_token": "refresh-token",
            "expires_at": int(time.time()) + 3600,
        }
    )
    with patch(
        "app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=token_data
    ):
        result = await get_valid_token(session, str(test_user.id))
    assert result == "valid-token"


async def test_get_valid_token_no_expires_at_triggers_refresh(session: AsyncSession, test_user):
    """When expires_at is missing/None, falls through to refresh."""
    token_data = json.dumps(
        {
            "access_token": "old-token",
            "refresh_token": "refresh-token",
            "expires_at": None,
        }
    )
    new_token_data = {
        "access_token": "refreshed-token",
        "refresh_token": "new-refresh",
        "expires_at": int(time.time()) + 3600,
    }

    with (
        patch(
            "app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=token_data
        ),
        patch(
            "app.services.swiggy.auth._refresh_token",
            new_callable=AsyncMock,
            return_value=new_token_data,
        ),
        patch("app.services.swiggy.auth.store_secret", new_callable=AsyncMock),
    ):
        result = await get_valid_token(session, str(test_user.id))

    assert result == "refreshed-token"


async def test_get_valid_token_expired_refreshes(session: AsyncSession, test_user):
    """Refreshes token when expired and returns new access_token."""
    token_data = json.dumps(
        {
            "access_token": "expired-token",
            "refresh_token": "refresh-token",
            "expires_at": int(time.time()) - 100,
        }
    )
    new_token_data = {
        "access_token": "new-token",
        "refresh_token": "new-refresh",
        "expires_at": int(time.time()) + 3600,
    }

    with (
        patch(
            "app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=token_data
        ),
        patch(
            "app.services.swiggy.auth._refresh_token",
            new_callable=AsyncMock,
            return_value=new_token_data,
        ),
        patch("app.services.swiggy.auth.store_secret", new_callable=AsyncMock) as mock_store,
    ):
        result = await get_valid_token(session, str(test_user.id))

    assert result == "new-token"
    mock_store.assert_called_once()


async def test_get_valid_token_refresh_fails_raises(session: AsyncSession, test_user):
    """Raises ProblemDetailError when refresh fails."""
    token_data = json.dumps(
        {
            "access_token": "expired-token",
            "refresh_token": "bad-refresh",
            "expires_at": int(time.time()) - 100,
        }
    )

    with (
        patch(
            "app.services.swiggy.auth.get_secret", new_callable=AsyncMock, return_value=token_data
        ),
        patch("app.services.swiggy.auth._refresh_token", new_callable=AsyncMock, return_value=None),
    ):
        with pytest.raises(ProblemDetailError) as exc_info:
            await get_valid_token(session, str(test_user.id))
        assert exc_info.value.status == 422


# --- _refresh_token tests ---


async def test_refresh_token_success():
    """Successful refresh returns new token data."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "expires_at": 1999999999,
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.swiggy.auth.httpx.AsyncClient", return_value=mock_client):
        result = await _refresh_token("old-refresh")

    assert result is not None
    assert result["access_token"] == "new-access"
    assert result["refresh_token"] == "new-refresh"
    assert result["expires_at"] == 1999999999


async def test_refresh_token_no_refresh_token_in_response():
    """If response doesn't include refresh_token, keeps the old one."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "new-access",
        "expires_at": 1999999999,
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.swiggy.auth.httpx.AsyncClient", return_value=mock_client):
        result = await _refresh_token("keep-this-refresh")

    assert result["refresh_token"] == "keep-this-refresh"


async def test_refresh_token_no_expires_at_extracts_from_jwt():
    """When expires_at not in response, extracts from JWT claims."""
    # Build a fake JWT with exp claim
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": "123", "exp": 2000000000}).encode())
        .rstrip(b"=")
        .decode()
    )
    fake_jwt = f"{header}.{payload}.signature"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": fake_jwt}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.swiggy.auth.httpx.AsyncClient", return_value=mock_client):
        result = await _refresh_token("refresh")

    assert result["expires_at"] == 2000000000


async def test_refresh_token_failure():
    """Non-200 response returns None."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.swiggy.auth.httpx.AsyncClient", return_value=mock_client):
        result = await _refresh_token("bad-refresh")

    assert result is None


# --- _extract_exp tests ---


def test_extract_exp_valid_jwt():
    """Extracts exp from a valid JWT payload."""
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": "user1", "exp": 1778162247}).encode())
        .rstrip(b"=")
        .decode()
    )
    token = f"header.{payload}.signature"
    assert _extract_exp(token) == 1778162247


def test_extract_exp_no_exp_claim():
    """Returns None when JWT has no exp claim."""
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "user1"}).encode()).rstrip(b"=").decode()
    token = f"header.{payload}.signature"
    assert _extract_exp(token) is None


def test_extract_exp_invalid_token():
    """Returns None for non-JWT string."""
    assert _extract_exp("not-a-jwt") is None
    assert _extract_exp("only.two") is None
