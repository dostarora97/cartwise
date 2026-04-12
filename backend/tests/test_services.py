"""Unit tests for classify and correlate services with mocked AI client."""

from unittest.mock import AsyncMock, patch

from app.services.classify import classify
from app.services.correlate import correlate

# --- classify ---


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
    assert result["summary"]["grand_total"] == 105.0
    assert len(result["items"]) == 2
    assert result["items"][0]["category"] == "item"
    assert result["items"][1]["category"] == "fee"
    assert mock_generate.call_count == 2


async def test_classify_empty_invoices():
    mock_generate = AsyncMock()

    with patch("app.services.classify.generate", mock_generate):
        result = await classify({"invoices": []})

    assert result["items"] == []
    assert result["summary"]["grand_total"] == 0
    mock_generate.assert_not_called()


async def test_classify_multiple_invoices():
    extracted = {
        "invoices": [
            {"page": 1, "items": [{"upc": "A", "description": "X", "total": 10.0}]},
            {"page": 2, "items": [{"upc": "B", "description": "Y", "total": 20.0}]},
        ]
    }

    mock_generate = AsyncMock(
        side_effect=[
            {"category": "item"},
            {"category": "item"},
        ]
    )

    with patch("app.services.classify.generate", mock_generate):
        result = await classify(extracted)

    assert len(result["items"]) == 2
    assert result["summary"]["item_total"] == 30.0


async def test_classify_progress_callback():
    extracted = {
        "invoices": [
            {
                "page": 1,
                "items": [
                    {"upc": "A", "description": "Item", "total": 10.0},
                    {"upc": "B", "description": "Fee", "total": 5.0},
                ],
            }
        ]
    }

    mock_generate = AsyncMock(side_effect=[{"category": "item"}, {"category": "fee"}])
    progress_calls = []

    def on_progress(current, total, category, description):
        progress_calls.append((current, total, category, description))

    with patch("app.services.classify.generate", mock_generate):
        await classify(extracted, on_progress=on_progress)

    assert len(progress_calls) == 2
    assert progress_calls[0] == (1, 2, "item", "Item")
    assert progress_calls[1] == (2, 2, "fee", "Fee")


# --- correlate ---


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
    menu_items = [{"id": "mi-1", "name": "Test", "ingredients": "stuff"}]
    grocery_items = [{"upc": "AAA", "description": "Real Item"}]

    mock_generate = AsyncMock(return_value={"matched_upcs": ["AAA", "FAKE-UPC"]})

    with patch("app.services.correlate.generate", mock_generate):
        uses = await correlate(menu_items, grocery_items)

    assert uses["mi-1"] == ["AAA"]


async def test_correlate_no_matches():
    menu_items = [{"id": "mi-1", "name": "Exotic", "ingredients": "truffle, saffron"}]
    grocery_items = [{"upc": "AAA", "description": "Onion"}]

    mock_generate = AsyncMock(return_value={"matched_upcs": []})

    with patch("app.services.correlate.generate", mock_generate):
        uses = await correlate(menu_items, grocery_items)

    assert uses["mi-1"] == []


async def test_correlate_empty_inputs():
    mock_generate = AsyncMock()

    with patch("app.services.correlate.generate", mock_generate):
        uses = await correlate([], [{"upc": "A", "description": "X"}])

    assert uses == {}
    mock_generate.assert_not_called()
