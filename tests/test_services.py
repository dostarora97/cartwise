"""Tests for classify and correlate services with mocked AI client."""

from unittest.mock import AsyncMock, patch

from app.services.classify import classify
from app.services.correlate import correlate


async def test_classify_items_and_fees():
    extracted = {
        "invoices": [
            {
                "page": 1,
                "items": [
                    {
                        "upc": "111",
                        "description": "Chicken",
                        "hsn": None,
                        "mrp": 100,
                        "qty": 1,
                        "total": 100.0,
                    },
                    {
                        "upc": "-",
                        "description": "Delivery charge",
                        "hsn": None,
                        "mrp": None,
                        "qty": None,
                        "total": 5.0,
                    },
                ],
                "invoice_total": 105.0,
            }
        ]
    }

    mock_generate = AsyncMock(
        side_effect=[
            {"category": "item"},
            {"category": "fee"},
        ]
    )

    with patch("app.services.classify.generate", mock_generate):
        result = await classify(extracted)

    assert result["summary"]["item_total"] == 100.0
    assert result["summary"]["fee_total"] == 5.0
    assert len(result["items"]) == 2
    assert result["items"][0]["category"] == "item"
    assert result["items"][1]["category"] == "fee"
    assert mock_generate.call_count == 2


async def test_correlate_matches_upcs():
    menu_items = [
        {"id": "mi-1", "name": "Chicken Curry", "ingredients": "chicken, onion, spices"},
        {"id": "mi-2", "name": "Salad", "ingredients": "cucumber, tomato"},
    ]
    grocery_items = [
        {"upc": "AAA", "description": "Chicken Breast"},
        {"upc": "BBB", "description": "Onion Pack"},
        {"upc": "CCC", "description": "Cucumber"},
    ]

    mock_generate = AsyncMock(
        side_effect=[
            {"matched_upcs": ["AAA", "BBB"]},
            {"matched_upcs": ["CCC"]},
        ]
    )

    with patch("app.services.correlate.generate", mock_generate):
        uses = await correlate(menu_items, grocery_items)

    assert uses["mi-1"] == ["AAA", "BBB"]
    assert uses["mi-2"] == ["CCC"]
    assert mock_generate.call_count == 2


async def test_correlate_filters_invalid_upcs():
    """Correlate should discard UPCs returned by LLM that don't exist in grocery items."""
    menu_items = [{"id": "mi-1", "name": "Test", "ingredients": "stuff"}]
    grocery_items = [{"upc": "AAA", "description": "Real Item"}]

    mock_generate = AsyncMock(return_value={"matched_upcs": ["AAA", "FAKE-UPC"]})

    with patch("app.services.correlate.generate", mock_generate):
        uses = await correlate(menu_items, grocery_items)

    assert uses["mi-1"] == ["AAA"]  # FAKE-UPC filtered out
