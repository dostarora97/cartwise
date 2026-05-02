"""Tests for Swiggy MCP dynamic client registration (RFC 7591)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.swiggy.registration import _registered_clients, ensure_client_registered


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the registration cache between tests."""
    _registered_clients.clear()
    yield
    _registered_clients.clear()


@pytest.mark.asyncio
async def test_registers_redirect_uri():
    """ensure_client_registered POSTs to /auth/register with correct payload."""
    mock_response = httpx.Response(
        201,
        json={
            "client_id": "swiggy-mcp",
            "client_name": "CartWise",
            "redirect_uris": ["https://example.com/auth/connect/swiggy"],
            "client_id_issued_at": 1777755801,
        },
        request=httpx.Request("POST", "http://localhost:8002/auth/register"),
    )

    with patch("app.services.swiggy.registration.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await ensure_client_registered("https://example.com/auth/connect/swiggy")

    assert result == "swiggy-mcp"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args[1]
    payload = call_kwargs["json"]
    assert payload["client_name"] == "CartWise"
    assert payload["redirect_uris"] == ["https://example.com/auth/connect/swiggy"]
    assert payload["token_endpoint_auth_method"] == "none"
    assert "mcp:tools" in payload["scope"]


@pytest.mark.asyncio
async def test_caches_registration():
    """Second call with same redirect_uri uses cache, no HTTP call."""
    mock_response = httpx.Response(
        201,
        json={"client_id": "swiggy-mcp", "client_id_issued_at": 1777755801},
        request=httpx.Request("POST", "http://localhost:8002/auth/register"),
    )

    with patch("app.services.swiggy.registration.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result1 = await ensure_client_registered("https://example.com/callback")
        result2 = await ensure_client_registered("https://example.com/callback")

    assert result1 == result2 == "swiggy-mcp"
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_raises_on_failure():
    """Non-2xx response raises httpx.HTTPStatusError."""
    mock_response = httpx.Response(
        403,
        json={"error": "forbidden"},
        request=httpx.Request("POST", "http://localhost:8002/auth/register"),
    )

    with patch("app.services.swiggy.registration.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await ensure_client_registered("https://example.com/callback")

    assert "https://example.com/callback" not in _registered_clients
