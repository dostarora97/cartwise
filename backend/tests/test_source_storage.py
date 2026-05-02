"""Tests for storage functions (local disk fallback + Supabase Storage branches)."""

import uuid
from unittest.mock import MagicMock, patch

from app.services.storage import (
    _source_storage_path,
    _storage_path,
    delete_order_files,
    delete_source_files,
    download_to_temp,
    save_source_upload,
    save_upload,
)


def test_source_storage_path():
    sid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
    assert (
        _source_storage_path(sid, "invoice.pdf")
        == "sources/12345678-1234-1234-1234-123456789abc/invoice.pdf"
    )


def test_save_source_upload_local(tmp_path):
    """save_source_upload writes to local disk when not real Supabase."""
    sid = uuid.uuid4()
    content = b"%PDF-1.4 fake content"

    with (
        patch("app.services.storage._is_real_supabase", return_value=False),
        patch("app.services.storage.settings") as mock_settings,
    ):
        mock_settings.get.return_value = str(tmp_path)
        result = save_source_upload(content, sid, "test.pdf")

    expected_path = tmp_path / "sources" / str(sid) / "test.pdf"
    assert expected_path.exists()
    assert expected_path.read_bytes() == content
    assert str(expected_path) == result


def test_delete_source_files_local(tmp_path):
    """delete_source_files removes the source directory."""
    sid = uuid.uuid4()
    source_dir = tmp_path / "sources" / str(sid)
    source_dir.mkdir(parents=True)
    (source_dir / "invoice.pdf").write_bytes(b"content")

    with (
        patch("app.services.storage._is_real_supabase", return_value=False),
        patch("app.services.storage.settings") as mock_settings,
    ):
        mock_settings.get.return_value = str(tmp_path)
        delete_source_files(sid)

    assert not source_dir.exists()


def test_delete_source_files_no_dir(tmp_path):
    """delete_source_files is a no-op if directory doesn't exist."""
    sid = uuid.uuid4()

    with (
        patch("app.services.storage._is_real_supabase", return_value=False),
        patch("app.services.storage.settings") as mock_settings,
    ):
        mock_settings.get.return_value = str(tmp_path)
        delete_source_files(sid)  # should not raise


# --- _storage_path ---


def test_storage_path():
    oid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert _storage_path(oid) == "orders/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/invoice.pdf"
    assert (
        _storage_path(oid, "receipt.pdf")
        == "orders/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/receipt.pdf"
    )


# --- Supabase Storage branches (mocked supabase client) ---


def test_save_upload_supabase():
    """save_upload calls Supabase Storage upload when real Supabase."""
    oid = uuid.uuid4()
    content = b"%PDF-1.4 data"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket

    with (
        patch("app.services.storage._is_real_supabase", return_value=True),
        patch("app.services.storage._get_supabase_client", return_value=mock_client),
    ):
        result = save_upload(content, oid)

    expected_path = f"orders/{oid}/invoice.pdf"
    mock_client.storage.from_.assert_called_once_with("invoices")
    mock_bucket.upload.assert_called_once_with(
        expected_path, content, file_options={"content-type": "application/pdf"}
    )
    assert result == expected_path


def test_save_upload_local(tmp_path):
    """save_upload writes to disk when not real Supabase."""
    oid = uuid.uuid4()
    content = b"%PDF-1.4 local"

    with (
        patch("app.services.storage._is_real_supabase", return_value=False),
        patch("app.services.storage.settings") as mock_settings,
    ):
        mock_settings.get.return_value = str(tmp_path)
        result = save_upload(content, oid)

    expected_file = tmp_path / "orders" / str(oid) / "invoice.pdf"
    assert expected_file.exists()
    assert expected_file.read_bytes() == content
    assert str(expected_file) == result


def test_download_to_temp_supabase():
    """download_to_temp downloads from Supabase and writes to tempfile."""
    mock_bucket = MagicMock()
    mock_bucket.download.return_value = b"%PDF-content"
    mock_client = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket

    with (
        patch("app.services.storage._is_real_supabase", return_value=True),
        patch("app.services.storage._get_supabase_client", return_value=mock_client),
    ):
        result = download_to_temp("orders/abc/invoice.pdf")

    assert result.endswith(".pdf")
    import os

    assert os.path.exists(result)
    with open(result, "rb") as f:
        assert f.read() == b"%PDF-content"
    os.unlink(result)


def test_download_to_temp_local():
    """download_to_temp returns path directly when not real Supabase."""
    with patch("app.services.storage._is_real_supabase", return_value=False):
        result = download_to_temp("/some/local/path.pdf")
    assert result == "/some/local/path.pdf"


def test_delete_order_files_supabase():
    """delete_order_files calls Supabase Storage remove."""
    oid = uuid.uuid4()

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket

    with (
        patch("app.services.storage._is_real_supabase", return_value=True),
        patch("app.services.storage._get_supabase_client", return_value=mock_client),
    ):
        delete_order_files(oid)

    expected_path = f"orders/{oid}/invoice.pdf"
    mock_bucket.remove.assert_called_once_with([expected_path])


def test_delete_order_files_local(tmp_path):
    """delete_order_files removes local directory."""
    oid = uuid.uuid4()
    order_dir = tmp_path / "orders" / str(oid)
    order_dir.mkdir(parents=True)
    (order_dir / "invoice.pdf").write_bytes(b"data")

    with (
        patch("app.services.storage._is_real_supabase", return_value=False),
        patch("app.services.storage.settings") as mock_settings,
    ):
        mock_settings.get.return_value = str(tmp_path)
        delete_order_files(oid)

    assert not order_dir.exists()


def test_save_source_upload_supabase():
    """save_source_upload calls Supabase Storage upload."""
    sid = uuid.uuid4()
    content = b"%PDF source"

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket

    with (
        patch("app.services.storage._is_real_supabase", return_value=True),
        patch("app.services.storage._get_supabase_client", return_value=mock_client),
    ):
        result = save_source_upload(content, sid, "receipt.pdf")

    expected_path = f"sources/{sid}/receipt.pdf"
    mock_bucket.upload.assert_called_once_with(
        expected_path, content, file_options={"content-type": "application/pdf"}
    )
    assert result == expected_path


def test_delete_source_files_supabase():
    """delete_source_files calls Supabase Storage remove."""
    sid = uuid.uuid4()

    mock_bucket = MagicMock()
    mock_client = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket

    with (
        patch("app.services.storage._is_real_supabase", return_value=True),
        patch("app.services.storage._get_supabase_client", return_value=mock_client),
    ):
        delete_source_files(sid)

    expected_path = f"sources/{sid}/invoice.pdf"
    mock_bucket.remove.assert_called_once_with([expected_path])
