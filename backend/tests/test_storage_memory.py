from app.infrastructure.storage.memory import InMemoryFileStorage


def test_upload_and_download_round_trip() -> None:
    storage = InMemoryFileStorage()
    key = storage.upload("docs/report.pdf", b"%PDF-1.4")

    assert storage.download(key) == b"%PDF-1.4"


def test_upload_returns_storage_key() -> None:
    storage = InMemoryFileStorage()

    assert storage.upload("a/b.pdf", b"data") == "a/b.pdf"


def test_exists_returns_false_for_missing_key() -> None:
    storage = InMemoryFileStorage()

    assert storage.exists("missing.pdf") is False


def test_exists_returns_true_after_upload() -> None:
    storage = InMemoryFileStorage()
    storage.upload("present.pdf", b"x")

    assert storage.exists("present.pdf") is True


def test_delete_removes_object() -> None:
    storage = InMemoryFileStorage()
    storage.upload("gone.pdf", b"x")

    storage.delete("gone.pdf")

    assert storage.exists("gone.pdf") is False


def test_download_raises_for_missing_key() -> None:
    storage = InMemoryFileStorage()

    try:
        storage.download("nope.pdf")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")
