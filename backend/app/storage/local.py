from __future__ import annotations

from pathlib import Path


class LocalFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def upload(self, path: str, data: bytes) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return path

    def download(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        return target.read_bytes()

    def delete(self, path: str) -> None:
        target = self._resolve(path)
        if target.is_file():
            target.unlink()

    def exists(self, path: str) -> bool:
        return self._resolve(path).is_file()

    def _resolve(self, path: str) -> Path:
        normalized = Path(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"Invalid storage path (path traversal): {path}")

        resolved = (self._base_dir / normalized).resolve()
        base = self._base_dir.resolve()
        if not resolved.is_relative_to(base):
            raise ValueError(f"Invalid storage path (path traversal): {path}")
        return resolved
