"""
File storage for uploaded invoices.

Saves PDFs to STORAGE_DIR/orders/{order_id}/invoice.pdf.
Abstracted so the backend can be swapped to S3/GCS later.
"""

import uuid
from pathlib import Path

from app.config import settings


def _order_dir(order_id: uuid.UUID) -> Path:
    return Path(settings.storage_dir) / "orders" / str(order_id)


def save_upload(content: bytes, order_id: uuid.UUID, filename: str = "invoice.pdf") -> str:
    """Save uploaded file content to disk.

    This is a sync function. In async context, call via:
        path = await asyncio.to_thread(save_upload, content, order_id)

    Args:
        content: Raw file bytes.
        order_id: UUID of the order (used as directory name).
        filename: Name to save as (default: invoice.pdf).

    Returns:
        Absolute path to the saved file as a string.
    """
    directory = _order_dir(order_id)
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename
    file_path.write_bytes(content)
    return str(file_path)
