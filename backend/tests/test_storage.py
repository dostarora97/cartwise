"""Unit tests for file storage — local fallback only, no Supabase."""

import uuid
from pathlib import Path

from app.services.storage import download_to_temp, save_upload


def test_save_upload_local_fallback(tmp_path, monkeypatch):
    """save_upload falls back to local disk when SUPABASE_URL is not real."""
    monkeypatch.setattr("app.services.storage.settings", _FakeSettings(storage_dir=str(tmp_path)))

    order_id = uuid.uuid4()
    content = b"%PDF-1.4 fake pdf content"

    path = save_upload(content, order_id, "invoice.pdf")

    assert Path(path).exists()
    assert Path(path).read_bytes() == content
    assert str(order_id) in path
    assert path.endswith("invoice.pdf")


def test_download_to_temp_local_fallback(tmp_path, monkeypatch):
    """download_to_temp returns the path as-is for local storage."""
    monkeypatch.setattr("app.services.storage.settings", _FakeSettings(storage_dir=str(tmp_path)))

    local_path = str(tmp_path / "test.pdf")
    Path(local_path).write_bytes(b"test content")

    result = download_to_temp(local_path)
    assert result == local_path


def test_save_upload_creates_directories(tmp_path, monkeypatch):
    """save_upload creates nested directories if they don't exist."""
    monkeypatch.setattr("app.services.storage.settings", _FakeSettings(storage_dir=str(tmp_path)))

    order_id = uuid.uuid4()
    path = save_upload(b"content", order_id)
    assert Path(path).parent.exists()


def test_save_upload_custom_filename(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage.settings", _FakeSettings(storage_dir=str(tmp_path)))

    order_id = uuid.uuid4()
    path = save_upload(b"content", order_id, "custom.pdf")
    assert path.endswith("custom.pdf")


class _FakeSettings:
    """Minimal settings stub for storage tests."""

    def __init__(self, storage_dir: str):
        self._storage_dir = storage_dir
        self.SUPABASE_URL = "http://test"  # Not https:// → triggers local fallback

    def get(self, key, default=None):
        if key == "SUPABASE_URL":
            return self.SUPABASE_URL
        if key == "STORAGE_DIR":
            return self._storage_dir
        return default
