from __future__ import annotations


class InMemoryFileStorage:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def upload(self, path: str, data: bytes) -> str:
        self._objects[path] = data
        return path

    def download(self, path: str) -> bytes:
        try:
            return self._objects[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    def delete(self, path: str) -> None:
        self._objects.pop(path, None)

    def exists(self, path: str) -> bool:
        return path in self._objects
