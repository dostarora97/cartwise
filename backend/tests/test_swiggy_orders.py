"""Tests for GET /orders/swiggy/orders endpoint."""

import json
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models.user import User


async def test_list_swiggy_orders_success(client: AsyncClient, auth_headers: dict, test_user: User):
    """Returns parsed orders from MCP tool call."""
    orders_data = [
        {"orderId": "SW-ORD-001", "restaurantName": "Biryani Blues", "totalAmount": 468},
        {"orderId": "SW-ORD-002", "restaurantName": "Biryani Blues", "totalAmount": 469},
    ]
    mock_result = json.dumps({"orders": orders_data})

    with (
        patch(
            "app.services.swiggy.auth.get_valid_token",
            new_callable=AsyncMock,
            return_value="valid-token",
        ),
        patch(
            "app.services.swiggy.client.call_tool",
            new_callable=AsyncMock,
            return_value="mcp-result",
        ),
        patch("app.services.swiggy.extract._extract_text", return_value=mock_result),
    ):
        resp = await client.get("/api/v1/orders/swiggy/orders", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["orderId"] == "SW-ORD-001"
    assert data[1]["totalAmount"] == 469


async def test_list_swiggy_orders_count_param(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    """Forwards count query parameter to MCP tool call."""
    mock_result = json.dumps({"orders": []})

    with (
        patch(
            "app.services.swiggy.auth.get_valid_token",
            new_callable=AsyncMock,
            return_value="valid-token",
        ),
        patch(
            "app.services.swiggy.client.call_tool",
            new_callable=AsyncMock,
            return_value="mcp-result",
        ) as mock_call,
        patch("app.services.swiggy.extract._extract_text", return_value=mock_result),
    ):
        resp = await client.get("/api/v1/orders/swiggy/orders?count=5", headers=auth_headers)

    assert resp.status_code == 200
    mock_call.assert_called_once_with("valid-token", "get_orders", {"count": 5})


async def test_list_swiggy_orders_count_max(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    """Rejects count > 20."""
    resp = await client.get("/api/v1/orders/swiggy/orders?count=50", headers=auth_headers)
    assert resp.status_code == 422


async def test_list_swiggy_orders_no_token_422(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    """Returns 422 when no Swiggy token exists (re-auth needed)."""
    from app.errors import ProblemDetailError

    with patch(
        "app.services.swiggy.auth.get_valid_token",
        new_callable=AsyncMock,
        side_effect=ProblemDetailError(
            type="swiggy_reauth_required",
            title="Re-authentication required",
            status=422,
            detail="Swiggy re-authentication required",
            provider="swiggy",
        ),
    ):
        resp = await client.get("/api/v1/orders/swiggy/orders", headers=auth_headers)

    assert resp.status_code == 422


async def test_list_swiggy_orders_no_auth(client: AsyncClient):
    """Returns 401 without auth headers."""
    resp = await client.get("/api/v1/orders/swiggy/orders")
    assert resp.status_code in (401, 403)


async def test_list_swiggy_orders_nested_data_format(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    """Handles nested data.orders format from MCP response."""
    orders_data = [{"orderId": "SW-ORD-003", "totalAmount": 200}]
    mock_result = json.dumps({"data": {"orders": orders_data}})

    with (
        patch(
            "app.services.swiggy.auth.get_valid_token",
            new_callable=AsyncMock,
            return_value="valid-token",
        ),
        patch(
            "app.services.swiggy.client.call_tool",
            new_callable=AsyncMock,
            return_value="mcp-result",
        ),
        patch("app.services.swiggy.extract._extract_text", return_value=mock_result),
    ):
        resp = await client.get("/api/v1/orders/swiggy/orders", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["orderId"] == "SW-ORD-003"
