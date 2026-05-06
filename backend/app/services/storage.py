"""
File storage for uploaded invoices using Supabase Storage.

Files are stored in the 'invoices' bucket at: orders/{order_id}/invoice.pdf

For local development/testing, falls back to local disk storage
when SUPABASE_URL is empty or set to a test value.
"""

import tempfile
import uuid
from pathlib import Path

from app.config import settings
from supabase import create_client

BUCKET = "invoices"


def _use_remote_storage() -> bool:
    """Check if remote (Supabase) storage should be used.

    Determined solely by STORAGE_LOCAL config flag — True in development/testing
    settings, absent/False in production.
    """
    return not settings.get("STORAGE_LOCAL", False)


def _get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


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
    if _use_remote_storage():
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
    if _use_remote_storage():
        client = _get_supabase_client()
        data = client.storage.from_(BUCKET).download(storage_path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            return tmp.name

    # Fallback: the storage_path IS the local path
    return storage_path


def delete_order_files(order_id: uuid.UUID) -> None:
    """Delete all stored files for an order.

    Sync function — call via asyncio.to_thread() in async context.
    """
    import shutil

    if _use_remote_storage():
        client = _get_supabase_client()
        path = _storage_path(order_id)
        client.storage.from_(BUCKET).remove([path])
        return

    local_dir = Path(settings.get("STORAGE_DIR", "./storage")) / "orders" / str(order_id)
    if local_dir.exists():
        shutil.rmtree(local_dir)


def _source_storage_path(source_id: uuid.UUID, filename: str) -> str:
    return f"sources/{source_id}/{filename}"


def save_source_upload(content: bytes, source_id: uuid.UUID, filename: str = "invoice.pdf") -> str:
    """Save uploaded file to storage under sources/{source_id}/.

    Sync function — call via asyncio.to_thread() in async context.
    """
    if _use_remote_storage():
        client = _get_supabase_client()
        path = _source_storage_path(source_id, filename)
        client.storage.from_(BUCKET).upload(
            path,
            content,
            file_options={"content-type": "application/pdf"},
        )
        return path

    local_dir = Path(settings.get("STORAGE_DIR", "./storage")) / "sources" / str(source_id)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / filename
    local_path.write_bytes(content)
    return str(local_path)


def delete_source_files(source_id: uuid.UUID) -> None:
    """Delete all stored files for a source.

    Sync function — call via asyncio.to_thread() in async context.
    """
    import shutil

    if _use_remote_storage():
        client = _get_supabase_client()
        path = _source_storage_path(source_id, "invoice.pdf")
        client.storage.from_(BUCKET).remove([path])
        return

    local_dir = Path(settings.get("STORAGE_DIR", "./storage")) / "sources" / str(source_id)
    if local_dir.exists():
        shutil.rmtree(local_dir)
