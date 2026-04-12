"""
Blinkit Invoice Row Classifier

Classifies each extracted grocery item as "item" (product) or "fee"
(order-level charge) using Ollama via async httpx.
"""

import json
from collections.abc import Callable

import httpx

from app.config import settings

MODEL = "qwen2.5:3b"

SYSTEM_PROMPT = (
    "You classify rows from a Blinkit grocery invoice. "
    'Each row is either an "item" (a product someone purchased) '
    'or a "fee" (an order-level charge like delivery, handling, packing, or service fees). '
    "Respond with the category only."
)

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": ["item", "fee"]}},
    "required": ["category"],
}


async def _classify_row(client: httpx.AsyncClient, row: dict) -> str:
    """Call Ollama to classify a single row. Returns 'item' or 'fee'."""
    response = await client.post(
        f"{settings.AI_BASE_URL}/api/generate",
        json={
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": f"Classify: {json.dumps(row)}",
            "format": CLASSIFY_SCHEMA,
            "stream": False,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return json.loads(response.json()["response"])["category"]


async def classify(
    extracted: dict,
    on_progress: Callable[[int, int, str, str], None] | None = None,
) -> dict:
    """Classify all items from an extracted invoice.

    Args:
        extracted: Output of extract(), with "invoices" key.
        on_progress: Optional callback(current, total, category, description)
                     called after each row is classified.

    Returns:
        Dict with "summary" and "items" keys.
    """
    all_rows = [row for invoice in extracted["invoices"] for row in invoice["items"]]

    classified_rows = []
    async with httpx.AsyncClient() as client:
        for i, row in enumerate(all_rows, 1):
            category = await _classify_row(client, row)
            classified_rows.append({**row, "category": category})
            if on_progress:
                on_progress(i, len(all_rows), category, row["description"])

    item_total = round(sum(r["total"] for r in classified_rows if r["category"] == "item"), 2)
    fee_total = round(sum(r["total"] for r in classified_rows if r["category"] == "fee"), 2)
    grand_total = round(item_total + fee_total, 2)

    return {
        "summary": {
            "item_total": item_total,
            "fee_total": fee_total,
            "grand_total": grand_total,
        },
        "items": classified_rows,
    }
