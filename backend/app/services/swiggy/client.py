"""Swiggy MCP client using FastMCP's StreamableHttp transport."""

from __future__ import annotations

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


async def call_tool(token: str, tool_name: str, arguments: dict) -> list:
    """Call a Swiggy MCP tool and return the result content."""
    transport = StreamableHttpTransport(
        url="https://mcp.swiggy.com/im",
        headers={"Authorization": f"Bearer {token}"},
    )
    async with Client(transport=transport) as client:
        result = await client.call_tool(tool_name, arguments)
        return result.content
