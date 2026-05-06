"""Extraction strategy dispatcher — routes source types to their extractors."""

from __future__ import annotations

import asyncio
from pathlib import Path

import logfire
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_source import OrderSource, OrderSourceType
from app.services.extract import extract
from app.services.storage import download_to_temp

logger = structlog.get_logger()


@logfire.instrument("run_extraction")
async def run_extraction(session: AsyncSession, source: OrderSource) -> list[dict]:
    """Run extraction for a source, using its checkpoint if available."""
    checkpoint_hit = source.items is not None
    logger.info(
        "extraction_start",
        source_id=str(source.id),
        source_type=source.type.value,
        checkpoint_hit=checkpoint_hit,
    )

    if source.items:
        logger.info("extraction_checkpoint_used", items_count=len(source.items))
        return source.items

    if source.type == OrderSourceType.invoice:
        items = await _extract_invoice(source)
    elif source.type == OrderSourceType.swiggy_order:
        items = await _extract_swiggy(session, source)
    else:
        raise ValueError(f"Unknown source type: {source.type}")

    source.items = items
    await session.flush()

    items_classified = sum(1 for i in items if i.get("category") == "item")
    fees_count = sum(1 for i in items if i.get("category") == "fee")
    logger.info(
        "extraction_complete",
        items_count=len(items),
        items_classified=items_classified,
        fees_count=fees_count,
    )

    return items


async def _extract_invoice(source: OrderSource) -> list[dict]:
    """Extract items from an invoice PDF source."""
    storage_path = source.raw_data.get("storage_path")
    if not storage_path:
        raise ValueError("Invoice source missing storage_path in raw_data")

    local_pdf = await asyncio.to_thread(download_to_temp, storage_path)
    try:
        extracted = await asyncio.to_thread(extract, local_pdf)
    finally:
        Path(local_pdf).unlink(missing_ok=True)

    from app.services.classify import classify

    classified = await classify(extracted)
    return classified["items"]


async def _extract_swiggy(session: AsyncSession, source: OrderSource) -> list[dict]:
    """Extract items from a Swiggy order source."""
    from app.services.swiggy.extract import extract_swiggy_order

    return await extract_swiggy_order(session, source)
