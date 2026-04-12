"""
Invoice Row Classifier

Classifies each extracted grocery item as "item" (product) or "fee"
(order-level charge) using the configured LLM via LiteLLM.
"""

import json
from collections.abc import Callable

from app.ai.client import generate

SYSTEM_PROMPT = (
    "You classify rows from a grocery invoice. "
    'Each row is either an "item" (a product someone purchased) '
    'or a "fee" (an order-level charge like delivery, handling, packing, or service fees). '
    "Respond with the category only."
)

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": ["item", "fee"]}},
    "required": ["category"],
}


async def _classify_row(row: dict) -> str:
    """Classify a single row. Returns 'item' or 'fee'."""
    result = await generate(
        system=SYSTEM_PROMPT,
        prompt=f"Classify: {json.dumps(row)}",
        schema=CLASSIFY_SCHEMA,
    )
    return result["category"]


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
    for i, row in enumerate(all_rows, 1):
        category = await _classify_row(row)
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
