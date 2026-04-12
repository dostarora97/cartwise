"""
File storage for uploaded invoices using Supabase Storage.

Files are stored in the 'invoices' bucket at: orders/{order_id}/invoice.pdf

For local development/testing, falls back to local disk storage
when SUPABASE_URL is empty or set to a test value.
"""

import tempfile
import uuid
from pathlib import Path

from supabase import create_client

from app.config import settings

BUCKET = "invoices"


def _is_real_supabase() -> bool:
    url = settings.get("SUPABASE_URL", "")
    return bool(url) and url.startswith("https://")


def _get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def _storage_path(order_id: uuid.UUID, filename: str = "invoice.pdf") -> str:
    return f"orders/{order_id}/{filename}"


def save_upload(content: bytes, order_id: uuid.UUID, filename: str = "invoice.pdf") -> str:
    """Save uploaded PDF to Supabase Storage (or local disk in test/dev fallback).

    This is a sync function. In async context, call via:
        path = await asyncio.to_thread(save_upload, content, order_id)

    Args:
        content: Raw file bytes.
        order_id: UUID of the order.
        filename: Name to save as (default: invoice.pdf).

    Returns:
        Storage path string (Supabase) or local file path (fallback).
    """
    if _is_real_supabase():
        client = _get_supabase_client()
        path = _storage_path(order_id, filename)
        client.storage.from_(BUCKET).upload(
            path,
            content,
            file_options={"content-type": "application/pdf"},
        )
        return path

    # Fallback: local disk (for testing and local dev without Supabase)
    local_dir = Path(settings.get("STORAGE_DIR", "./storage")) / "orders" / str(order_id)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / filename
    local_path.write_bytes(content)
    return str(local_path)


def download_to_temp(storage_path: str) -> str:
    """Download a file from storage to a temporary local file.

    Needed because pdfplumber requires a local file path.

    Returns:
        Path to the temporary file.
    """
    if _is_real_supabase():
        client = _get_supabase_client()
        data = client.storage.from_(BUCKET).download(storage_path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            return tmp.name

    # Fallback: the storage_path IS the local path
    return storage_path
