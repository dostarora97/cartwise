"""Tests for Swiggy order extraction with mocked MCP calls."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_source import OrderSource, OrderSourceType
from app.services.swiggy.extract import (
    _build_items,
    _extract_fees,
    _extract_text,
    _find_order,
    _strip_quantity_prefix,
    extract_swiggy_order,
)


def test_strip_quantity_prefix():
    assert _strip_quantity_prefix("2 x Milk") == "Milk"
    assert _strip_quantity_prefix("1 x Bread") == "Bread"
    assert _strip_quantity_prefix("Eggs") == "Eggs"
    assert _strip_quantity_prefix("10 x Rice") == "Rice"


def test_extract_text_success():
    block = MagicMock()
    block.text = '{"data": "value"}'
    result = _extract_text([block])
    assert result == '{"data": "value"}'


def test_extract_text_no_text():
    block = MagicMock(spec=[])  # no 'text' attribute
    with pytest.raises(ValueError, match="No text content"):
        _extract_text([block])


def test_find_order_found():
    orders_data = {"orders": [{"orderId": "123", "items": []}, {"orderId": "456", "items": []}]}
    result = _find_order(orders_data, "456")
    assert result == {"orderId": "456", "items": []}


def test_find_order_not_found():
    orders_data = {"orders": [{"orderId": "123"}]}
    result = _find_order(orders_data, "999")
    assert result is None


def test_find_order_nested_data():
    orders_data = {"data": {"orders": [{"order_id": "789", "items": []}]}}
    result = _find_order(orders_data, "789")
    assert result == {"order_id": "789", "items": []}


def test_build_items_basic():
    order_info = {
        "items": [
            {"itemId": "I1", "name": "Milk", "quantity": 2, "total": 90},
            {"itemId": "I2", "name": "Bread", "quantity": 1, "total": 40},
        ]
    }
    track_data = {
        "items": [
            {"name": "2 x Milk", "total": 90},
            {"name": "1 x Bread", "total": 40},
        ],
        "billDetails": {"deliveryFee": 25, "handlingFee": 0},
    }

    items = _build_items(order_info, track_data)

    product_items = [i for i in items if i["category"] == "item"]
    fee_items = [i for i in items if i["category"] == "fee"]

    assert len(product_items) == 2
    assert product_items[0]["name"] == "Milk"
    assert product_items[0]["total"] == 90.0
    assert product_items[1]["name"] == "Bread"
    assert product_items[1]["total"] == 40.0

    assert len(fee_items) == 1
    assert fee_items[0]["name"] == "Delivery Fee"
    assert fee_items[0]["total"] == 25.0


def test_extract_fees_multiple():
    track_data = {
        "billDetails": {
            "deliveryFee": 30,
            "handlingFee": 5,
            "platformFee": 3,
            "packagingCharges": 0,
            "surgeFee": 0,
        }
    }
    fees = _extract_fees(track_data)
    assert len(fees) == 3
    names = [f["name"] for f in fees]
    assert "Delivery Fee" in names
    assert "Handling Fee" in names
    assert "Platform Fee" in names


def test_extract_fees_nested():
    track_data = {"data": {"billDetails": {"deliveryFee": 15}}}
    fees = _extract_fees(track_data)
    assert len(fees) == 1
    assert fees[0]["total"] == 15.0


async def test_extract_swiggy_order_full(session: AsyncSession, test_user):
    """Full extraction flow with mocked MCP client."""
    source = OrderSource(
        type=OrderSourceType.swiggy_order,
        raw_data={"swiggy_order_id": "ORD123"},
        created_by=test_user.id,
    )
    session.add(source)
    await session.flush()

    orders_block = MagicMock()
    orders_block.text = json.dumps(
        {
            "orders": [
                {"orderId": "ORD123", "items": [{"itemId": "A", "name": "Eggs", "quantity": 6}]}
            ]
        }
    )

    track_block = MagicMock()
    track_block.text = json.dumps(
        {
            "items": [{"name": "6 x Eggs", "total": 78}],
            "billDetails": {"deliveryFee": 20, "handlingFee": 0},
        }
    )

    with (
        patch(
            "app.services.swiggy.extract.get_valid_token",
            new_callable=AsyncMock,
            return_value="fake-token",
        ),
        patch(
            "app.services.swiggy.extract.call_tool",
            new_callable=AsyncMock,
            side_effect=[[orders_block], [track_block]],
        ),
    ):
        items = await extract_swiggy_order(session, source)

    product_items = [i for i in items if i["category"] == "item"]
    fee_items = [i for i in items if i["category"] == "fee"]

    assert len(product_items) == 1
    assert product_items[0]["name"] == "Eggs"
    assert product_items[0]["total"] == 78.0
    assert product_items[0]["quantity"] == 6

    assert len(fee_items) == 1
    assert fee_items[0]["name"] == "Delivery Fee"

    # raw_data should be updated
    assert "orders_response" in source.raw_data
    assert "track_response" in source.raw_data


async def test_extract_swiggy_order_missing_order_id(session: AsyncSession, test_user):
    """Raises ValueError if swiggy_order_id not in raw_data."""
    source = OrderSource(
        type=OrderSourceType.swiggy_order,
        raw_data={},
        created_by=test_user.id,
    )
    session.add(source)
    await session.flush()

    with (
        patch(
            "app.services.swiggy.extract.get_valid_token",
            new_callable=AsyncMock,
            return_value="token",
        ),
        pytest.raises(ValueError, match="swiggy_order_id"),
    ):
        await extract_swiggy_order(session, source)
