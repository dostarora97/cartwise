"""Swiggy order extraction — fetches order data and normalizes to items."""

from __future__ import annotations

import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_source import OrderSource
from app.services.swiggy.auth import get_valid_token
from app.services.swiggy.client import call_tool


async def extract_swiggy_order(session: AsyncSession, source: OrderSource) -> list[dict]:
    """Fetch Swiggy order details and normalize into CartWise items.

    Calls get_orders + track_order, joins by name, and returns items
    in the standard format: [{id, name, quantity, total, category}, ...]
    """
    token = await get_valid_token(session, str(source.created_by))

    swiggy_order_id = source.raw_data.get("swiggy_order_id")
    if not swiggy_order_id:
        raise ValueError("source.raw_data must contain 'swiggy_order_id'")

    # Fetch order list to get item names and IDs
    orders_result = await call_tool(token, "get_orders", {"count": 20})
    orders_text = _extract_text(orders_result)
    orders_data = json.loads(orders_text)

    # Find the specific order
    order_info = _find_order(orders_data, swiggy_order_id)
    if not order_info:
        raise ValueError(f"Order {swiggy_order_id} not found in recent Swiggy orders")

    # Track order to get per-item prices
    track_result = await call_tool(
        token,
        "track_order",
        {"orderId": swiggy_order_id, "lat": 0, "lng": 0},
    )
    track_text = _extract_text(track_result)
    track_data = json.loads(track_text)

    # Join data and build normalized items
    items = _build_items(order_info, track_data)

    # Update source raw_data with API responses
    source.raw_data = {
        **source.raw_data,
        "orders_response": orders_data,
        "track_response": track_data,
    }

    return items


def _extract_text(content: list) -> str:
    """Extract text from MCP tool result content blocks."""
    for block in content:
        if hasattr(block, "text"):
            return block.text
    raise ValueError("No text content in MCP response")


def _find_order(orders_data: dict, order_id: str) -> dict | None:
    """Find a specific order in the get_orders response."""
    orders = orders_data.get("orders", orders_data.get("data", {}).get("orders", []))
    if isinstance(orders, list):
        for order in orders:
            oid = str(order.get("orderId", order.get("order_id", "")))
            if oid == order_id:
                return order
    return None


def _build_items(order_info: dict, track_data: dict) -> list[dict]:
    """Join order items with tracking prices and build normalized item list."""
    # Extract items from order_info
    order_items = order_info.get("items", order_info.get("orderItems", []))

    # Extract items from track_data for prices
    track_items = _extract_track_items(track_data)

    # Build price lookup from track data (strip "N x " prefix for matching)
    price_by_name: dict[str, float] = {}
    for ti in track_items:
        name = _strip_quantity_prefix(ti.get("name", ""))
        price_by_name[name.lower()] = ti.get("total", ti.get("price", 0))

    items: list[dict] = []
    for item in order_items:
        name = item.get("name", item.get("itemName", ""))
        quantity = item.get("quantity", item.get("qty", 1))
        item_id = str(item.get("itemId", item.get("item_id", name)))

        # Try to find price from track data
        total = price_by_name.get(name.lower(), item.get("total", item.get("price", 0)))

        items.append(
            {
                "id": item_id,
                "upc": item_id,
                "name": name,
                "description": name,
                "quantity": quantity,
                "total": float(total),
                "category": "item",
            }
        )

    # Synthesize fee items from bill details
    fees = _extract_fees(track_data)
    items.extend(fees)

    return items


def _extract_track_items(track_data: dict) -> list[dict]:
    """Extract item list from track_order response."""
    # Handle various response shapes
    if "items" in track_data:
        return track_data["items"]
    if "data" in track_data and "items" in track_data["data"]:
        return track_data["data"]["items"]
    if "orderDetails" in track_data:
        return track_data["orderDetails"].get("items", [])
    return []


def _extract_fees(track_data: dict) -> list[dict]:
    """Synthesize fee line items from bill details."""
    fees = []
    bill = (
        track_data.get("billDetails")
        or track_data.get("data", {}).get("billDetails")
        or track_data.get("orderDetails", {}).get("billDetails")
        or {}
    )

    fee_mappings = [
        ("deliveryFee", "Delivery Fee"),
        ("handlingFee", "Handling Fee"),
        ("platformFee", "Platform Fee"),
        ("packagingCharges", "Packaging Charges"),
        ("surgeFee", "Surge Fee"),
    ]

    for key, display_name in fee_mappings:
        value = bill.get(key, 0)
        if value and float(value) > 0:
            fees.append(
                {
                    "id": f"FEE_{key.upper()}",
                    "upc": f"FEE_{key.upper()}",
                    "name": display_name,
                    "description": display_name,
                    "quantity": 1,
                    "total": float(value),
                    "category": "fee",
                }
            )

    return fees


def _strip_quantity_prefix(name: str) -> str:
    """Strip 'N x ' prefix from item names (e.g., '2 x Milk' → 'Milk')."""
    return re.sub(r"^\d+\s*x\s*", "", name)
