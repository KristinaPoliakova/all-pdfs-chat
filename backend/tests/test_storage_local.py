from pathlib import Path

import pytest
from app.infrastructure.storage.local import LocalFileStorage


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def storage(storage_dir: Path) -> LocalFileStorage:
    return LocalFileStorage(storage_dir)


def test_upload_persists_bytes_on_disk(storage: LocalFileStorage, storage_dir: Path) -> None:
    key = storage.upload("docs/report.pdf", b"%PDF-1.4")

    assert (storage_dir / key).read_bytes() == b"%PDF-1.4"


def test_download_reads_uploaded_file(storage: LocalFileStorage) -> None:
    storage.upload("file.pdf", b"hello")

    assert storage.download("file.pdf") == b"hello"


def test_exists_reflects_disk_state(storage: LocalFileStorage) -> None:
    assert storage.exists("missing.pdf") is False

    storage.upload("here.pdf", b"x")

    assert storage.exists("here.pdf") is True


def test_delete_removes_file_from_disk(storage: LocalFileStorage, storage_dir: Path) -> None:
    storage.upload("remove.pdf", b"x")

    storage.delete("remove.pdf")

    assert not (storage_dir / "remove.pdf").exists()
    assert storage.exists("remove.pdf") is False


def test_rejects_path_traversal(storage: LocalFileStorage) -> None:
    with pytest.raises(ValueError, match="path traversal"):
        storage.upload("../escape.pdf", b"bad")


def test_download_raises_for_missing_key(storage: LocalFileStorage) -> None:
    with pytest.raises(FileNotFoundError):
        storage.download("missing.pdf")
