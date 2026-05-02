"""Tests for Swiggy OAuth connect/exchange and _extract_sub."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.routes.auth import _extract_sub


def test_extract_sub_valid_jwt():
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": "swiggy-user-42", "exp": 9999999999}).encode())
        .rstrip(b"=")
        .decode()
    )
    token = f"header.{payload}.signature"
    assert _extract_sub(token) == "swiggy-user-42"


def test_extract_sub_no_sub():
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": 9999999999}).encode()).rstrip(b"=").decode()
    )
    token = f"header.{payload}.signature"
    assert _extract_sub(token) is None


def test_extract_sub_invalid_token():
    assert _extract_sub("not-a-jwt") is None
    assert _extract_sub("only.two") is None


async def test_swiggy_connect(client: AsyncClient, auth_headers: dict, test_user):
    """POST /auth/swiggy/connect returns authorize_url, redirect_uri, code_verifier."""
    resp = await client.post("/api/v1/auth/swiggy/connect", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "authorize_url" in data
    assert "redirect_uri" in data
    assert "code_verifier" in data
    assert "code_challenge" in data["authorize_url"]
    assert "S256" in data["authorize_url"]
    assert "/auth/connect/swiggy" in data["redirect_uri"]


async def test_swiggy_connect_no_auth(client: AsyncClient):
    """Connect without auth returns 401/403."""
    resp = await client.post("/api/v1/auth/swiggy/connect")
    assert resp.status_code in (401, 403)


async def test_swiggy_exchange_invalid_state(client: AsyncClient):
    """Exchange with bad state returns 400."""
    resp = await client.post(
        "/api/v1/auth/swiggy/exchange",
        json={
            "code": "auth-code",
            "state": "bad-state-token",
            "code_verifier": "verifier",
            "redirect_uri": "http://localhost:3000/auth/connect/swiggy",
        },
    )
    assert resp.status_code == 400


async def test_swiggy_exchange_success(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Successful exchange stores tokens and updates user."""
    # Build a fake JWT for the token response
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": "swiggy-user-99", "exp": 9999999999}).encode())
        .rstrip(b"=")
        .decode()
    )
    fake_jwt = f"header.{payload}.signature"

    # First get a valid state by calling connect
    connect_resp = await client.post("/api/v1/auth/swiggy/connect", headers=auth_headers)
    state = connect_resp.json()["authorize_url"].split("state=")[1].split("&")[0]

    # Mock the httpx POST to Swiggy token endpoint
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": fake_jwt,
        "refresh_token": "refresh-abc",
    }

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_http_client),
        patch("app.routes.auth.store_secret", new_callable=AsyncMock) as mock_store,
    ):
        resp = await client.post(
            "/api/v1/auth/swiggy/exchange",
            json={
                "code": "valid-code",
                "state": state,
                "code_verifier": "test-verifier",
                "redirect_uri": "http://localhost:3000/auth/connect/swiggy",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_store.assert_called_once()
    stored_name = mock_store.call_args.args[1]
    assert f"swiggy_token:{test_user.id}" == stored_name


async def test_swiggy_exchange_token_failure(client: AsyncClient, auth_headers: dict, test_user):
    """Exchange returns 502 when Swiggy token endpoint fails."""
    connect_resp = await client.post("/api/v1/auth/swiggy/connect", headers=auth_headers)
    state = connect_resp.json()["authorize_url"].split("state=")[1].split("&")[0]

    mock_response = MagicMock()
    mock_response.status_code = 400

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        resp = await client.post(
            "/api/v1/auth/swiggy/exchange",
            json={
                "code": "bad-code",
                "state": state,
                "code_verifier": "verifier",
                "redirect_uri": "http://localhost:3000/auth/connect/swiggy",
            },
        )

    assert resp.status_code == 502


async def test_swiggy_exchange_no_access_token(client: AsyncClient, auth_headers: dict, test_user):
    """Exchange returns 502 when response has no access_token."""
    connect_resp = await client.post("/api/v1/auth/swiggy/connect", headers=auth_headers)
    state = connect_resp.json()["authorize_url"].split("state=")[1].split("&")[0]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"refresh_token": "only-refresh"}

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        resp = await client.post(
            "/api/v1/auth/swiggy/exchange",
            json={
                "code": "code",
                "state": state,
                "code_verifier": "verifier",
                "redirect_uri": "http://localhost:3000/auth/connect/swiggy",
            },
        )

    assert resp.status_code == 502
    assert "No access token" in resp.json()["detail"]
