"""Tests for Swiggy MCP client wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.services.swiggy.client import call_tool


async def test_call_tool_returns_content():
    """call_tool wraps FastMCP Client and returns result.content."""
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='{"items": []}')]

    mock_client = AsyncMock()
    mock_client.call_tool.return_value = mock_result
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.swiggy.client.Client", return_value=mock_client):
        result = await call_tool("fake-token", "get_orders", {"count": 10})

    assert result == mock_result.content
    mock_client.call_tool.assert_called_once_with("get_orders", {"count": 10})
