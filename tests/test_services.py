"""Tests for classify and correlate services with mocked Ollama."""

import json
from unittest.mock import AsyncMock, patch

import httpx

from app.services.classify import classify
from app.services.correlate import correlate


def _mock_ollama_classify(category: str):
    """Create a mock response for classify."""
    return httpx.Response(
        200,
        json={"response": json.dumps({"category": category})},
        request=httpx.Request("POST", "http://mock"),
    )


def _mock_ollama_correlate(upcs: list[str]):
    """Create a mock response for correlate."""
    return httpx.Response(
        200,
        json={"response": json.dumps({"matched_upcs": upcs})},
        request=httpx.Request("POST", "http://mock"),
    )


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

    responses = [
        _mock_ollama_classify("item"),
        _mock_ollama_classify("fee"),
    ]

    with patch("app.services.classify.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=responses)
        mock_client_cls.return_value = mock_client

        result = await classify(extracted)

    assert result["summary"]["item_total"] == 100.0
    assert result["summary"]["fee_total"] == 5.0
    assert len(result["items"]) == 2
    assert result["items"][0]["category"] == "item"
    assert result["items"][1]["category"] == "fee"


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

    responses = [
        _mock_ollama_correlate(["AAA", "BBB"]),  # Chicken Curry matches
        _mock_ollama_correlate(["CCC"]),  # Salad matches
    ]

    with patch("app.services.correlate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=responses)
        mock_client_cls.return_value = mock_client

        uses = await correlate(menu_items, grocery_items)

    assert uses["mi-1"] == ["AAA", "BBB"]
    assert uses["mi-2"] == ["CCC"]


async def test_correlate_filters_invalid_upcs():
    """Correlate should discard UPCs returned by LLM that don't exist in grocery items."""
    menu_items = [{"id": "mi-1", "name": "Test", "ingredients": "stuff"}]
    grocery_items = [{"upc": "AAA", "description": "Real Item"}]

    responses = [
        _mock_ollama_correlate(["AAA", "FAKE-UPC"]),  # FAKE-UPC doesn't exist
    ]

    with patch("app.services.correlate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=responses)
        mock_client_cls.return_value = mock_client

        uses = await correlate(menu_items, grocery_items)

    assert uses["mi-1"] == ["AAA"]  # FAKE-UPC filtered out
