"""
Invoice Row Classifier

Classifies each extracted grocery item as "item" (product) or "fee"
(order-level charge) using the configured LLM via LiteLLM.
"""

import asyncio
import json
from collections.abc import Callable

import logfire
import structlog

from app.ai.client import generate

logger = structlog.get_logger()

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


@logfire.instrument("classify_row")
async def _classify_row(row: dict) -> str:
    """Classify a single row. Returns 'item' or 'fee'."""
    result = await generate(
        system=SYSTEM_PROMPT,
        prompt=f"Classify: {json.dumps(row)}",
        schema=CLASSIFY_SCHEMA,
    )
    return result["category"]


@logfire.instrument("classify {total_items} items")
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
    total_items = len(all_rows)

    logger.info("classify_start", total_items=total_items)

    categories = await asyncio.gather(*[_classify_row(row) for row in all_rows])

    classified_rows = []
    for i, (row, category) in enumerate(zip(all_rows, categories, strict=True), 1):
        classified_rows.append({**row, "category": category})

        logger.info(
            "classify_row",
            item_index=i,
            total_items=total_items,
            description=row["description"],
            category_result=category,
        )

        if on_progress:
            on_progress(i, total_items, category, row["description"])

    item_total = round(sum(r["total"] for r in classified_rows if r["category"] == "item"), 2)
    fee_total = round(sum(r["total"] for r in classified_rows if r["category"] == "fee"), 2)
    grand_total = round(item_total + fee_total, 2)

    items_count = sum(1 for r in classified_rows if r["category"] == "item")
    fees_count = sum(1 for r in classified_rows if r["category"] == "fee")
    logger.info(
        "classify_complete",
        items_count=items_count,
        fees_count=fees_count,
        item_total=item_total,
        fee_total=fee_total,
    )

    return {
        "summary": {
            "item_total": item_total,
            "fee_total": fee_total,
            "grand_total": grand_total,
        },
        "items": classified_rows,
    }
