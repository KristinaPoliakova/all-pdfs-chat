from __future__ import annotations

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient


class AzureBlobStorage:
    def __init__(self, *, connection_string: str, container_name: str) -> None:
        self._container_name = container_name
        self._client = BlobServiceClient.from_connection_string(connection_string)
        self._container = self._client.get_container_client(container_name)

    def upload(self, path: str, data: bytes) -> str:
        blob = self._container.get_blob_client(path)
        blob.upload_blob(data, overwrite=True)
        return path

    def download(self, path: str) -> bytes:
        blob = self._container.get_blob_client(path)
        try:
            return blob.download_blob().readall()
        except ResourceNotFoundError as exc:
            raise FileNotFoundError(path) from exc

    def delete(self, path: str) -> None:
        blob = self._container.get_blob_client(path)
        try:
            blob.delete_blob()
        except ResourceNotFoundError:
            pass

    def exists(self, path: str) -> bool:
        blob = self._container.get_blob_client(path)
        return blob.exists()

    def close(self) -> None:
        self._client.close()
