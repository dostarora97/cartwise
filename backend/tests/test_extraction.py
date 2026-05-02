"""Tests for the extraction strategy dispatcher."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_source import OrderSource, OrderSourceType
from app.services.extraction import run_extraction


async def test_run_extraction_returns_checkpoint(session: AsyncSession, test_user):
    """If source.items is already populated, returns it directly (checkpoint)."""
    source = OrderSource(
        type=OrderSourceType.invoice,
        raw_data={"storage_path": "/fake/path"},
        items=[{"id": "1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"}],
        created_by=test_user.id,
    )
    session.add(source)
    await session.flush()

    result = await run_extraction(session, source)
    assert result == source.items


async def test_run_extraction_invoice(session: AsyncSession, test_user):
    """Invoice source runs PDF extraction pipeline."""
    source = OrderSource(
        type=OrderSourceType.invoice,
        raw_data={"storage_path": "/fake/invoice.pdf"},
        created_by=test_user.id,
    )
    session.add(source)
    await session.flush()

    mock_items = [
        {"id": "1", "name": "Rice", "quantity": 1, "total": 80.0, "category": "item"},
        {"id": "FEE_DELIVERY", "name": "Delivery", "quantity": 1, "total": 10.0, "category": "fee"},
    ]

    with (
        patch("app.services.extraction.download_to_temp", return_value="/tmp/fake.pdf"),
        patch("app.services.extraction.extract", return_value={"invoices": []}),
        patch(
            "app.services.classify.classify",
            new_callable=AsyncMock,
            return_value={"items": mock_items},
        ),
        patch("pathlib.Path.unlink"),
    ):
        result = await run_extraction(session, source)

    assert result == mock_items
    assert source.items == mock_items


async def test_run_extraction_swiggy(session: AsyncSession, test_user):
    """Swiggy source calls extract_swiggy_order."""
    source = OrderSource(
        type=OrderSourceType.swiggy_order,
        raw_data={"swiggy_order_id": "12345"},
        created_by=test_user.id,
    )
    session.add(source)
    await session.flush()

    mock_items = [
        {"id": "item1", "name": "Bread", "quantity": 2, "total": 60.0, "category": "item"},
    ]

    with patch(
        "app.services.extraction._extract_swiggy",
        new_callable=AsyncMock,
        return_value=mock_items,
    ):
        result = await run_extraction(session, source)

    assert result == mock_items
    assert source.items == mock_items


async def test_run_extraction_unknown_type(session: AsyncSession, test_user):
    """Unknown source type raises ValueError."""
    source = OrderSource(
        type=OrderSourceType.invoice,
        raw_data={},
        created_by=test_user.id,
    )
    session.add(source)
    await session.flush()

    # Monkey-patch type to something invalid
    source.type = "unknown"

    with pytest.raises(ValueError, match="Unknown source type"):
        await run_extraction(session, source)
