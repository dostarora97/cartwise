"""
Mock Swiggy MCP Server

A FastMCP server + OAuth endpoints that mimic the Swiggy MCP surface.
Returns canned order data for `get_orders` and `track_order` tools.

Run: uv run uvicorn mock.swiggy_mcp:app --port 8002
URL: http://localhost:8002/mcp (MCP tools)
     http://localhost:8002/auth/authorize (OAuth)
     http://localhost:8002/auth/token (token exchange + refresh)
"""

import base64
import json
import time
import uuid

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route

# --- Canned data ---

ORDERS = [
    {
        "orderId": "SW-ORD-001",
        "restaurantName": "Biryani Blues",
        "orderDate": "2026-04-30T19:30:00Z",
        "totalAmount": 468,
        "status": "delivered",
        "items": [
            {"itemId": "BB-001", "name": "Chicken Biryani", "quantity": 1},
            {"itemId": "BB-002", "name": "Raita", "quantity": 1},
            {"itemId": "BB-003", "name": "Coke", "quantity": 1},
        ],
    },
    {
        "orderId": "SW-ORD-002",
        "restaurantName": "Biryani Blues",
        "orderDate": "2026-04-28T20:15:00Z",
        "totalAmount": 469,
        "status": "delivered",
        "items": [
            {"itemId": "BB-004", "name": "Paneer Tikka", "quantity": 1},
            {"itemId": "BB-005", "name": "Naan", "quantity": 2},
            {"itemId": "BB-006", "name": "Lassi", "quantity": 1},
        ],
    },
]

TRACK_DATA = {
    "SW-ORD-001": {
        "orderId": "SW-ORD-001",
        "restaurantName": "Biryani Blues",
        "status": "delivered",
        "items": [
            {"name": "1 x Chicken Biryani", "total": 349},
            {"name": "1 x Raita", "total": 49},
            {"name": "1 x Coke", "total": 40},
        ],
        "billDetails": {
            "itemTotal": 438,
            "deliveryFee": 30,
            "platformFee": 5,
            "packagingCharges": 15,
            "totalPayable": 488,
        },
    },
    "SW-ORD-002": {
        "orderId": "SW-ORD-002",
        "restaurantName": "Biryani Blues",
        "status": "delivered",
        "items": [
            {"name": "1 x Paneer Tikka", "total": 279},
            {"name": "2 x Naan", "total": 80},
            {"name": "1 x Lassi", "total": 60},
        ],
        "billDetails": {
            "itemTotal": 419,
            "deliveryFee": 30,
            "platformFee": 5,
            "packagingCharges": 15,
            "totalPayable": 469,
        },
    },
}

# --- MCP Server (tools) ---

mcp = FastMCP("Swiggy Mock MCP")


@mcp.tool()
def get_orders(count: int = 10) -> str:
    """Get recent Swiggy orders."""
    return json.dumps({"orders": ORDERS[:count]})


@mcp.tool()
def track_order(orderId: str, lat: float = 0, lng: float = 0) -> str:  # noqa: N803
    """Track a specific Swiggy order with item prices and bill details."""
    data = TRACK_DATA.get(orderId)
    if not data:
        return json.dumps({"error": f"Order {orderId} not found"})
    return json.dumps(data)


# --- Helper ---


def _make_jwt(sub: str = "swiggy-mock-user", expires_in: int = 3600) -> str:
    """Create a minimal mock JWT (not cryptographically signed, just base64)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(
        b"="
    )
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {
                "sub": sub,
                "exp": int(time.time()) + expires_in,
                "iat": int(time.time()),
            }
        ).encode()
    ).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.mock-signature"


# --- OAuth + debug routes ---


async def authorize(request: Request):
    """Mock OAuth authorize — immediately redirects back with a code."""
    redirect_uri = request.query_params.get("redirect_uri", "")
    state = request.query_params.get("state", "")
    code = f"mock_swiggy_code_{uuid.uuid4().hex[:8]}"
    return RedirectResponse(f"{redirect_uri}?code={code}&state={state}")


async def token(request: Request):
    """Mock token exchange — returns a fake JWT access token."""
    access_token = _make_jwt()
    refresh_token = f"mock_refresh_{uuid.uuid4().hex[:8]}"
    return JSONResponse(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
        }
    )


async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "mock-swiggy-mcp"})


async def list_canned_orders(request: Request):
    """Debug: see all canned orders."""
    return JSONResponse({"orders": ORDERS, "track_data": TRACK_DATA})


# --- Compose the app ---
# Starlette routes are checked in order. OAuth/debug routes first,
# then MCP app mounted at /mcp (which is where FastMCP registers its handler).

mcp_http = mcp.http_app()

app = Starlette(
    routes=[
        Route("/auth/authorize", authorize, methods=["GET"]),
        Route("/auth/token", token, methods=["POST"]),
        Route("/_health", health, methods=["GET"]),
        Route("/_orders", list_canned_orders, methods=["GET"]),
        Mount("/", app=mcp_http),
    ],
    lifespan=mcp_http.lifespan,
)
