from unittest.mock import MagicMock, patch

import pytest
from app.storage.azure import AzureBlobStorage
from azure.core.exceptions import ResourceNotFoundError


@pytest.fixture
def blob_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def container_client(blob_client: MagicMock) -> MagicMock:
    container = MagicMock()
    container.get_blob_client.return_value = blob_client
    return container


@pytest.fixture
def storage(container_client: MagicMock) -> AzureBlobStorage:
    with patch("app.storage.azure.BlobServiceClient") as service_ctor:
        service = MagicMock()
        service.get_container_client.return_value = container_client
        service_ctor.from_connection_string.return_value = service
        yield AzureBlobStorage(
            connection_string="UseDevelopmentStorage=true",
            container_name="pdfs",
        )


def test_upload_writes_blob(storage: AzureBlobStorage, blob_client: MagicMock) -> None:
    key = storage.upload("docs/report.pdf", b"%PDF-1.4")

    assert key == "docs/report.pdf"
    blob_client.upload_blob.assert_called_once_with(b"%PDF-1.4", overwrite=True)


def test_download_reads_blob(storage: AzureBlobStorage, blob_client: MagicMock) -> None:
    blob_client.download_blob.return_value.readall.return_value = b"payload"

    assert storage.download("docs/report.pdf") == b"payload"


def test_download_raises_when_blob_missing(
    storage: AzureBlobStorage, blob_client: MagicMock
) -> None:
    blob_client.download_blob.side_effect = ResourceNotFoundError("missing")

    with pytest.raises(FileNotFoundError):
        storage.download("missing.pdf")


def test_exists_delegates_to_blob_client(storage: AzureBlobStorage, blob_client: MagicMock) -> None:
    blob_client.exists.return_value = True

    assert storage.exists("here.pdf") is True


def test_delete_calls_blob_client(storage: AzureBlobStorage, blob_client: MagicMock) -> None:
    storage.delete("gone.pdf")

    blob_client.delete_blob.assert_called_once()
